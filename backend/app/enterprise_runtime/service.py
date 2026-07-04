from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import EnterpriseQueueStatus, EventStatus, NotificationTriggerType, ODataCacheStatus, ResolverType, RunMode, RunStatus
from app.core.errors import BadRequestError, NotFoundError
from app.enterprise_runtime.models import (
    BusinessRuleDefinition,
    CanonicalBusinessObject,
    DeadLetterQueueItem,
    IntegrationQueueMessage,
    ODataCacheEntry,
    QueueAttempt,
    ResolverDefinition,
)
from app.enterprise_runtime.rules import run_rules
from app.enterprise_runtime.schemas import BusinessRuleCreate, CanonicalObjectCreate, QueueMessageCreate, QueueMessagePatch, ResolverCreate
from app.enterprise_runtime.transforms import apply_transform
from app.events.models import IntegrationEvent
from app.events.service import replay_event
from app.execution.engine import ExecutionEngine
from app.notifications.service import trigger_notifications

CANONICAL_OBJECTS = [
    "Customer", "Supplier", "Product", "Warehouse", "Location", "SalesOrder", "PurchaseOrder", "Shipment", "ShipmentFact", "StockBalance", "InventoryResult", "PrintJob",
]
RETRY_DELAYS_SECONDS = [60, 300, 900, 1800, 3600, 7200, 14400]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def create_queue_message(session: AsyncSession, request: QueueMessageCreate) -> IntegrationQueueMessage:
    data = request.model_dump()
    if not data.get("original_payload_json"):
        data["original_payload_json"] = data.get("payload_json") or {}
    message = IntegrationQueueMessage(**data, status=EnterpriseQueueStatus.WAITING, timeline_link=f"/events/{request.event_id}" if request.event_id else None)
    session.add(message)
    await session.flush()
    return message


async def ensure_queue_for_event(
    session: AsyncSession,
    *,
    event_id: UUID,
    message_id: UUID | None,
    business_object: str | None,
    operation: str | None,
    workflow_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
    endpoint_id: UUID | None = None,
    route_id: UUID | None = None,
    source_system: str | None = None,
    target_system: str | None = None,
    business_key: str | None = None,
    priority: int = 100,
    max_attempts: int = 10,
) -> IntegrationQueueMessage:
    result = await session.execute(select(IntegrationQueueMessage).where(IntegrationQueueMessage.event_id == event_id).limit(1))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    request = QueueMessageCreate(
        event_id=event_id,
        message_id=message_id,
        endpoint_id=endpoint_id,
        route_id=route_id,
        workflow_id=workflow_id,
        business_object=business_object or "IntegrationEvent",
        business_key=business_key,
        operation=operation or "process",
        source_system=source_system,
        target_system=target_system,
        priority=priority,
        max_attempts=max_attempts,
        payload_json=payload or {},
        original_payload_json=payload or {},
    )
    return await create_queue_message(session, request)


async def list_queue(
    session: AsyncSession,
    status: EnterpriseQueueStatus | None = None,
    business_object: str | None = None,
    operation: str | None = None,
    source_system: str | None = None,
    target_system: str | None = None,
    business_key: str | None = None,
    has_error: bool | None = None,
    sort: str = "priority",
) -> list[IntegrationQueueMessage]:
    query = select(IntegrationQueueMessage).order_by(IntegrationQueueMessage.priority.asc(), IntegrationQueueMessage.created_at.desc())
    if status:
        query = query.where(IntegrationQueueMessage.status == status)
    if business_object:
        query = query.where(IntegrationQueueMessage.business_object == business_object)
    if operation:
        query = query.where(IntegrationQueueMessage.operation == operation)
    if source_system:
        query = query.where(IntegrationQueueMessage.source_system == source_system)
    if target_system:
        query = query.where(IntegrationQueueMessage.target_system == target_system)
    if business_key:
        query = query.where(IntegrationQueueMessage.business_key == business_key)
    if has_error is True:
        query = query.where(IntegrationQueueMessage.last_error.is_not(None))
    if has_error is False:
        query = query.where(IntegrationQueueMessage.last_error.is_(None))
    sort_columns = {
        "priority": (IntegrationQueueMessage.priority.asc(), IntegrationQueueMessage.created_at.desc()),
        "created_at": (IntegrationQueueMessage.created_at.desc(),),
        "next_retry_at": (IntegrationQueueMessage.next_retry_at.asc().nulls_last(), IntegrationQueueMessage.priority.asc()),
        "attempts": (IntegrationQueueMessage.attempts.desc(), IntegrationQueueMessage.created_at.desc()),
    }
    query = query.order_by(*sort_columns.get(sort, sort_columns["priority"]))
    return list((await session.execute(query)).scalars().all())


async def get_queue_or_404(session: AsyncSession, queue_id: UUID) -> IntegrationQueueMessage:
    item = await session.get(IntegrationQueueMessage, queue_id)
    if item is None:
        raise NotFoundError("Queue message not found")
    return item


async def patch_queue(session: AsyncSession, queue_id: UUID, request: QueueMessagePatch) -> IntegrationQueueMessage:
    item = await get_queue_or_404(session, queue_id)
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    if request.status == EnterpriseQueueStatus.COMPLETED:
        item.completed_at = utcnow()
    await session.flush()
    return item


async def mark_processing(session: AsyncSession, queue_id: UUID, worker: str) -> IntegrationQueueMessage:
    item = await get_queue_or_404(session, queue_id)
    lock_item(item, worker)
    await session.flush()
    return item


async def move_to_dlq(session: AsyncSession, queue_id: UUID, reason: str) -> DeadLetterQueueItem:
    item = await get_queue_or_404(session, queue_id)
    dlq = await _move_item_to_dlq(session, item, reason)
    await trigger_notifications(session, NotificationTriggerType.QUEUE_ITEM_DLQ, {"queue_item_id": str(item.id), "reason": reason, "business_object": item.business_object, "operation": item.operation})
    return dlq


async def _move_item_to_dlq(session: AsyncSession, item: IntegrationQueueMessage, reason: str) -> DeadLetterQueueItem:
    item.status = EnterpriseQueueStatus.DLQ
    item.last_error = reason
    item.last_error_message = reason
    item.finished_at = utcnow()
    _clear_lock(item)
    dlq = DeadLetterQueueItem(
        queue_message_id=item.id,
        event_id=item.event_id,
        message_id=item.message_id,
        business_object=item.business_object,
        operation=item.operation,
        reason=reason,
        payload_json=item.original_payload_json or item.payload_json,
        current_payload_json=item.payload_json,
        last_error=item.last_error,
        attempts=item.attempts,
        timeline_link=item.timeline_link,
    )
    session.add(dlq)
    await session.flush()
    return dlq


async def list_dlq(session: AsyncSession, include_archived: bool = False) -> list[DeadLetterQueueItem]:
    query = select(DeadLetterQueueItem).order_by(DeadLetterQueueItem.created_at.desc())
    if not include_archived:
        query = query.where(DeadLetterQueueItem.archived.is_(False))
    return list((await session.execute(query)).scalars().all())


async def get_dlq_or_404(session: AsyncSession, item_id: UUID) -> DeadLetterQueueItem:
    item = await session.get(DeadLetterQueueItem, item_id)
    if item is None:
        raise NotFoundError("DLQ item not found")
    return item


async def retry_dlq(session: AsyncSession, item_id: UUID) -> IntegrationQueueMessage:
    item = await get_dlq_or_404(session, item_id)
    queue = await session.get(IntegrationQueueMessage, item.queue_message_id) if item.queue_message_id else None
    if queue is None:
        queue = IntegrationQueueMessage(event_id=item.event_id, message_id=item.message_id, business_object=item.business_object, operation=item.operation, payload_json=item.payload_json, timeline_link=item.timeline_link)
        session.add(queue)
    queue.status = EnterpriseQueueStatus.WAITING
    queue.last_error = None
    queue.last_error_code = None
    queue.last_error_message = None
    queue.next_retry_at = None
    _clear_lock(queue)
    item.restored_at = utcnow()
    await session.flush()
    return queue


async def edit_retry_dlq(session: AsyncSession, item_id: UUID, payload_json: dict[str, Any]) -> IntegrationQueueMessage:
    queue = await retry_dlq(session, item_id)
    queue.payload_json = payload_json
    await session.flush()
    return queue


async def replay_dlq(session: AsyncSession, item_id: UUID):
    item = await get_dlq_or_404(session, item_id)
    if item.event_id is None:
        raise BadRequestError("DLQ item is not linked to an event")
    return await replay_event(session, item.event_id)


async def archive_dlq(session: AsyncSession, item_id: UUID) -> DeadLetterQueueItem:
    item = await get_dlq_or_404(session, item_id)
    item.archived = True
    item.archived_at = utcnow()
    await session.flush()
    return item


async def retry_now(session: AsyncSession, queue_id: UUID) -> IntegrationQueueMessage:
    item = await get_queue_or_404(session, queue_id)
    item.status = EnterpriseQueueStatus.WAITING
    item.next_retry_at = None
    item.last_error = None
    _clear_lock(item)
    await session.flush()
    return item


async def cancel_queue(session: AsyncSession, queue_id: UUID) -> IntegrationQueueMessage:
    item = await get_queue_or_404(session, queue_id)
    item.status = EnterpriseQueueStatus.CANCELLED
    item.finished_at = utcnow()
    _clear_lock(item)
    await session.flush()
    return item


async def force_complete_queue(session: AsyncSession, queue_id: UUID) -> IntegrationQueueMessage:
    item = await get_queue_or_404(session, queue_id)
    item.status = EnterpriseQueueStatus.COMPLETED
    item.completed_at = utcnow()
    item.finished_at = item.completed_at
    _clear_lock(item)
    await session.flush()
    return item


async def unlock_queue(session: AsyncSession, queue_id: UUID) -> IntegrationQueueMessage:
    item = await get_queue_or_404(session, queue_id)
    _clear_lock(item)
    if item.status == EnterpriseQueueStatus.PROCESSING:
        item.status = EnterpriseQueueStatus.WAITING
    await session.flush()
    return item


async def eligible_queue_item(session: AsyncSession, worker: str = "worker") -> IntegrationQueueMessage | None:
    now = utcnow()
    result = await session.execute(
        select(IntegrationQueueMessage)
        .where(IntegrationQueueMessage.status.in_([EnterpriseQueueStatus.WAITING, EnterpriseQueueStatus.RETRY_WAITING]))
        .where(or_(IntegrationQueueMessage.next_retry_at.is_(None), IntegrationQueueMessage.next_retry_at <= now))
        .where(or_(IntegrationQueueMessage.locked_until.is_(None), IntegrationQueueMessage.locked_until < now))
        .order_by(IntegrationQueueMessage.priority.asc(), IntegrationQueueMessage.created_at.asc())
        .limit(1)
    )
    item = result.scalar_one_or_none()
    if item is None:
        return None
    lock_item(item, worker)
    await session.flush()
    return item


def lock_item(item: IntegrationQueueMessage, worker: str) -> None:
    now = utcnow()
    item.status = EnterpriseQueueStatus.PROCESSING
    item.worker = worker
    item.locked_by = worker
    item.locked_at = now
    item.locked_until = now + timedelta(seconds=get_settings().queue_lock_seconds)
    item.started_at = item.started_at or now
    item.attempts += 1


async def process_once(session: AsyncSession, worker: str = "manual-worker") -> IntegrationQueueMessage | None:
    item = await eligible_queue_item(session, worker)
    if item is None:
        return None
    return await process_locked_item(session, item)


async def process_batch(session: AsyncSession, limit: int | None = None, worker: str = "manual-worker") -> list[IntegrationQueueMessage]:
    processed: list[IntegrationQueueMessage] = []
    for _ in range(limit or get_settings().queue_worker_batch_size):
        item = await process_once(session, worker)
        if item is None:
            break
        processed.append(item)
        await session.flush()
    return processed


async def process_locked_item(session: AsyncSession, item: IntegrationQueueMessage) -> IntegrationQueueMessage:
    started = utcnow()
    attempt = QueueAttempt(queue_message_id=item.id, attempt_no=item.attempts, status="processing", started_at=started)
    session.add(attempt)
    await session.flush()
    try:
        if item.event_id is None:
            raise BadRequestError("QUEUE_ITEM_HAS_NO_EVENT")
        event = await session.get(IntegrationEvent, item.event_id)
        if event is None:
            raise NotFoundError("Queue event not found")
        run = await ExecutionEngine(session).execute_event(event.id, mode=RunMode.NORMAL, initial_payload=item.payload_json, workflow_id=item.workflow_id)
        item.run_id = run.id
        attempt.run_id = run.id
        if run.status == RunStatus.SUCCESS:
            item.status = EnterpriseQueueStatus.COMPLETED
            item.completed_at = utcnow()
            item.finished_at = item.completed_at
            item.last_error = None
            item.last_error_code = None
            item.last_error_message = None
        elif event.status == EventStatus.RETRY_WAITING:
            await schedule_retry_or_dlq(session, item, "RETRY_WAITING", "Workflow requested retry")
        else:
            await schedule_retry_or_dlq(session, item, "PIPELINE_FAILED", "Pipeline failed")
        attempt.status = item.status.value
    except Exception as exc:
        await schedule_retry_or_dlq(session, item, _classify_error_code(exc), str(exc) or exc.__class__.__name__)
        attempt.status = item.status.value
    finally:
        finished = utcnow()
        attempt.finished_at = finished
        attempt.error_code = item.last_error_code
        attempt.error_message = item.last_error_message
        attempt.duration_ms = _duration_ms(started, finished)
        _clear_lock(item)
        await session.flush()
    return item


async def schedule_retry_or_dlq(session: AsyncSession, item: IntegrationQueueMessage, error_code: str, error_message: str) -> None:
    item.last_error_code = error_code
    item.last_error_message = error_message
    item.last_error = error_message
    item.finished_at = utcnow()
    retryable = _is_retryable(error_code, error_message)
    if not retryable:
        item.status = EnterpriseQueueStatus.FAILED
        await _move_item_to_dlq(session, item, error_message)
        return
    if item.attempts >= item.max_attempts:
        await trigger_notifications(session, NotificationTriggerType.RETRY_EXHAUSTED, {"queue_item_id": str(item.id), "attempts": item.attempts, "error": error_message})
        await _move_item_to_dlq(session, item, error_message)
        return
    item.status = EnterpriseQueueStatus.RETRY_WAITING
    item.next_retry_at = utcnow() + timedelta(seconds=retry_delay_seconds(item.attempts))


def retry_delay_seconds(attempts: int) -> int:
    index = max(0, min(attempts - 1, len(RETRY_DELAYS_SECONDS) - 1))
    return RETRY_DELAYS_SECONDS[index]


async def list_attempts(session: AsyncSession, queue_id: UUID) -> list[QueueAttempt]:
    return list((await session.execute(select(QueueAttempt).where(QueueAttempt.queue_message_id == queue_id).order_by(QueueAttempt.attempt_no.asc()))).scalars().all())


async def monitor_summary(session: AsyncSession) -> dict[str, int]:
    result = await session.execute(select(IntegrationQueueMessage.status, func.count()).group_by(IntegrationQueueMessage.status))
    counts = {status.value if hasattr(status, "value") else str(status): count for status, count in result.all()}
    dlq_count = await session.scalar(select(func.count()).select_from(DeadLetterQueueItem).where(DeadLetterQueueItem.archived.is_(False)))
    counts["dlq"] = int(dlq_count or counts.get("dlq", 0))
    return counts


async def worker_health(session: AsyncSession) -> dict[str, Any]:
    now = utcnow()
    oldest_waiting = await session.scalar(select(func.min(IntegrationQueueMessage.created_at)).where(IntegrationQueueMessage.status == EnterpriseQueueStatus.WAITING))
    oldest_retry = await session.scalar(select(func.min(IntegrationQueueMessage.next_retry_at)).where(IntegrationQueueMessage.status == EnterpriseQueueStatus.RETRY_WAITING))
    stuck = await session.scalar(select(func.count()).select_from(IntegrationQueueMessage).where(IntegrationQueueMessage.status == EnterpriseQueueStatus.PROCESSING, IntegrationQueueMessage.locked_until < now))
    counts = await monitor_summary(session)
    return {"component": "Queue Worker", "oldest_waiting": oldest_waiting, "oldest_retry": oldest_retry, "stuck_processing": int(stuck or 0), "dlq": counts.get("dlq", 0)}


async def list_canonical_objects(session: AsyncSession) -> list[CanonicalBusinessObject]:
    return list((await session.execute(select(CanonicalBusinessObject).order_by(CanonicalBusinessObject.name))).scalars().all())


async def upsert_canonical_object(session: AsyncSession, request: CanonicalObjectCreate) -> CanonicalBusinessObject:
    result = await session.execute(select(CanonicalBusinessObject).where(CanonicalBusinessObject.name == request.name))
    item = result.scalar_one_or_none()
    if item is None:
        item = CanonicalBusinessObject(**request.model_dump(by_alias=True))
        session.add(item)
    else:
        item.description = request.description
        item.schema_json = request.schema_
        item.active = request.active
    await session.flush()
    return item


async def install_canonical_presets(session: AsyncSession) -> list[CanonicalBusinessObject]:
    created = []
    for name in CANONICAL_OBJECTS:
        created.append(await upsert_canonical_object(session, CanonicalObjectCreate(name=name, description=f"Canonical {name} business object", schema_json={"type": "object", "title": name})))
    return created


async def list_resolvers(session: AsyncSession) -> list[ResolverDefinition]:
    return list((await session.execute(select(ResolverDefinition).order_by(ResolverDefinition.name))).scalars().all())


async def upsert_resolver(session: AsyncSession, request: ResolverCreate) -> ResolverDefinition:
    result = await session.execute(select(ResolverDefinition).where(ResolverDefinition.name == request.name))
    item = result.scalar_one_or_none()
    if item is None:
        item = ResolverDefinition(**request.model_dump())
        session.add(item)
    else:
        for key, value in request.model_dump().items():
            setattr(item, key, value)
    await session.flush()
    return item


async def resolve(session: AsyncSession, resolver_id: UUID, input_values: dict[str, Any], lookup_key: str | None, use_cache: bool = True) -> dict[str, Any]:
    resolver = await session.get(ResolverDefinition, resolver_id)
    if resolver is None:
        raise NotFoundError("Resolver not found")
    key = lookup_key or _lookup_key(resolver, input_values)
    if use_cache:
        cached = await _get_cache(session, resolver.name, key)
        if cached:
            return {"resolver": resolver.name, "cache_status": ODataCacheStatus.HIT, "lookup_key": key, "value": cached.value_json}
    value = await _resolve_value(resolver, input_values)
    await preload_cache(session, resolver.name, key, value or {}, resolver.cache_ttl_seconds)
    return {"resolver": resolver.name, "cache_status": ODataCacheStatus.MISS, "lookup_key": key, "value": value}


async def list_rules(session: AsyncSession) -> list[BusinessRuleDefinition]:
    return list((await session.execute(select(BusinessRuleDefinition).order_by(BusinessRuleDefinition.name))).scalars().all())


async def upsert_rule(session: AsyncSession, request: BusinessRuleCreate) -> BusinessRuleDefinition:
    result = await session.execute(select(BusinessRuleDefinition).where(BusinessRuleDefinition.name == request.name))
    item = result.scalar_one_or_none()
    if item is None:
        item = BusinessRuleDefinition(**request.model_dump())
        session.add(item)
    else:
        for key, value in request.model_dump().items():
            setattr(item, key, value)
    await session.flush()
    return item


async def run_rule(session: AsyncSession, rule_id: UUID, payload: dict[str, Any]) -> dict[str, Any]:
    rule = await session.get(BusinessRuleDefinition, rule_id)
    if rule is None:
        raise NotFoundError("Business rule not found")
    return run_rules(rule.rules_json, payload)


async def list_cache(session: AsyncSession) -> list[ODataCacheEntry]:
    return list((await session.execute(select(ODataCacheEntry).order_by(ODataCacheEntry.updated_at.desc()))).scalars().all())


async def preload_cache(session: AsyncSession, resolver_name: str, lookup_key: str, value_json: dict[str, Any], ttl_seconds: int = 3600) -> ODataCacheEntry:
    result = await session.execute(select(ODataCacheEntry).where(ODataCacheEntry.resolver_name == resolver_name, ODataCacheEntry.lookup_key == lookup_key))
    item = result.scalar_one_or_none()
    if item is None:
        item = ODataCacheEntry(resolver_name=resolver_name, lookup_key=lookup_key)
        session.add(item)
    item.status = ODataCacheStatus.HIT
    item.value_json = value_json
    item.expires_at = utcnow() + timedelta(seconds=ttl_seconds)
    await session.flush()
    return item


async def invalidate_cache(session: AsyncSession, cache_id: UUID) -> ODataCacheEntry:
    item = await session.get(ODataCacheEntry, cache_id)
    if item is None:
        raise NotFoundError("OData cache entry not found")
    item.status = ODataCacheStatus.INVALIDATED
    item.expires_at = utcnow()
    await session.flush()
    return item


async def apply_transform_by_name(name: str, value: Any, params: dict[str, Any]) -> Any:
    try:
        return apply_transform(name, value, params)
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc


async def install_runtime_presets(session: AsyncSession) -> dict[str, Any]:
    objects = await install_canonical_presets(session)
    resolvers = [
        await upsert_resolver(session, ResolverCreate(name="ResolveCustomer", resolver_type=ResolverType.CACHE, business_object="Customer", config_json={"key": "inn"})),
        await upsert_resolver(session, ResolverCreate(name="ResolveProduct", resolver_type=ResolverType.CACHE, business_object="Product", config_json={"key": "sku"})),
        await upsert_resolver(session, ResolverCreate(name="ResolveWarehouse", resolver_type=ResolverType.CACHE, business_object="Warehouse", config_json={"key": "warehouse_id"})),
        await upsert_resolver(session, ResolverCreate(name="ResolveLocation", resolver_type=ResolverType.CACHE, business_object="Location", config_json={"key": "location_id"})),
        await upsert_resolver(session, ResolverCreate(name="ResolveOrder", resolver_type=ResolverType.CACHE, business_object="SalesOrder", config_json={"key": "order_id"})),
        await upsert_resolver(session, ResolverCreate(name="ResolvePrinter", resolver_type=ResolverType.CACHE, business_object="PrintJob", config_json={"key": "printer"})),
    ]
    rule = await upsert_rule(session, BusinessRuleCreate(name="Stop cancelled orders", business_object="SalesOrder", operation="ship", rules_json=[{"action": "FAIL", "if": {"field": "status", "op": "eq", "value": "cancelled"}, "message": "Cancelled order cannot be shipped"}]))
    return {"canonical_objects": len(objects), "resolvers": len(resolvers), "rules": [rule.name]}


async def _get_cache(session: AsyncSession, resolver_name: str, lookup_key: str) -> ODataCacheEntry | None:
    result = await session.execute(select(ODataCacheEntry).where(ODataCacheEntry.resolver_name == resolver_name, ODataCacheEntry.lookup_key == lookup_key))
    item = result.scalar_one_or_none()
    if item is None or item.status == ODataCacheStatus.INVALIDATED:
        return None
    if item.expires_at and _is_expired(item.expires_at):
        item.status = ODataCacheStatus.STALE
        return None
    item.hit_count += 1
    item.last_hit_at = utcnow()
    return item


def _is_expired(value: datetime) -> bool:
    expires_at = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return expires_at < utcnow()


def _lookup_key(resolver: ResolverDefinition, input_values: dict[str, Any]) -> str:
    key_name = str((resolver.config_json or {}).get("key") or "id")
    return str(input_values.get(key_name) or input_values.get("id") or input_values)


async def _resolve_value(resolver: ResolverDefinition, input_values: dict[str, Any]) -> dict[str, Any] | None:
    if resolver.resolver_type == ResolverType.CACHE:
        key_name = str((resolver.config_json or {}).get("key") or "id")
        return {"resolved": False, "key": input_values.get(key_name), "source": "cache_miss"}
    if resolver.resolver_type == ResolverType.REST:
        return {"resolved": False, "source": "rest_not_configured", "input": input_values}
    if resolver.resolver_type == ResolverType.ODATA:
        return {"resolved": False, "source": "odata_not_configured", "input": input_values}
    return None


def _clear_lock(item: IntegrationQueueMessage) -> None:
    item.locked_by = None
    item.locked_at = None
    item.locked_until = None
    item.worker = None


def _duration_ms(started: datetime | None, finished: datetime | None) -> int | None:
    if not started or not finished:
        return None
    return int((finished - started).total_seconds() * 1000)


def _classify_error_code(exc: Exception) -> str:
    text = f"{exc.__class__.__name__} {exc}".lower()
    if any(marker in text for marker in ("timeout", "connection", "offline", "maintenance", "temporar")):
        return "TECHNICAL_RETRYABLE"
    if any(marker in text for marker in ("validation", "mapping", "lookup_not_found", "business", "rejection")):
        return "BUSINESS_NON_RETRYABLE"
    return "TECHNICAL_RETRYABLE"


def _is_retryable(error_code: str, error_message: str) -> bool:
    text = f"{error_code} {error_message}".lower()
    if any(marker in text for marker in ("validation", "mapping", "lookup_not_found", "business_non_retryable", "business rejection")):
        return False
    return any(marker in text for marker in ("retry", "timeout", "connection", "5", "maintenance", "printer", "offline", "pipeline_failed", "unexpected"))


def _latest_error_from_run(run: Any) -> str | None:
    steps = sorted(getattr(run, "steps", []) or [], key=lambda step: step.step_order, reverse=True)
    for step in steps:
        if step.error_message:
            return step.error_message
    return None
