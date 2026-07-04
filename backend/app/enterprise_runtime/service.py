from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import EnterpriseQueueStatus, ODataCacheStatus, ResolverType
from app.core.errors import BadRequestError, NotFoundError
from app.enterprise_runtime.models import (
    BusinessRuleDefinition,
    CanonicalBusinessObject,
    DeadLetterQueueItem,
    IntegrationQueueMessage,
    ODataCacheEntry,
    ResolverDefinition,
)
from app.enterprise_runtime.rules import run_rules
from app.enterprise_runtime.schemas import BusinessRuleCreate, CanonicalObjectCreate, QueueMessageCreate, QueueMessagePatch, ResolverCreate
from app.enterprise_runtime.transforms import apply_transform
from app.events.service import replay_event

CANONICAL_OBJECTS = [
    "Customer", "Supplier", "Product", "Warehouse", "Location", "SalesOrder", "PurchaseOrder", "Shipment", "ShipmentFact", "StockBalance", "InventoryResult", "PrintJob",
]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def create_queue_message(session: AsyncSession, request: QueueMessageCreate) -> IntegrationQueueMessage:
    message = IntegrationQueueMessage(**request.model_dump(), status=EnterpriseQueueStatus.WAITING, timeline_link=f"/events/{request.event_id}" if request.event_id else None)
    session.add(message)
    await session.flush()
    return message


async def ensure_queue_for_event(session: AsyncSession, *, event_id: UUID, message_id: UUID | None, business_object: str | None, operation: str | None, workflow_id: UUID | None = None, payload: dict[str, Any] | None = None) -> IntegrationQueueMessage:
    result = await session.execute(select(IntegrationQueueMessage).where(IntegrationQueueMessage.event_id == event_id).limit(1))
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    request = QueueMessageCreate(event_id=event_id, message_id=message_id, workflow_id=workflow_id, business_object=business_object or "IntegrationEvent", operation=operation or "process", payload_json=payload or {})
    return await create_queue_message(session, request)


async def list_queue(session: AsyncSession, status: EnterpriseQueueStatus | None = None, business_object: str | None = None, operation: str | None = None) -> list[IntegrationQueueMessage]:
    query = select(IntegrationQueueMessage).order_by(IntegrationQueueMessage.priority.asc(), IntegrationQueueMessage.created_at.desc())
    if status:
        query = query.where(IntegrationQueueMessage.status == status)
    if business_object:
        query = query.where(IntegrationQueueMessage.business_object == business_object)
    if operation:
        query = query.where(IntegrationQueueMessage.operation == operation)
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
    item.status = EnterpriseQueueStatus.PROCESSING
    item.worker = worker
    item.locked_at = utcnow()
    item.attempts += 1
    await session.flush()
    return item


async def move_to_dlq(session: AsyncSession, queue_id: UUID, reason: str) -> DeadLetterQueueItem:
    item = await get_queue_or_404(session, queue_id)
    item.status = EnterpriseQueueStatus.DLQ
    item.last_error = reason
    dlq = DeadLetterQueueItem(queue_message_id=item.id, event_id=item.event_id, message_id=item.message_id, business_object=item.business_object, operation=item.operation, reason=reason, payload_json=item.payload_json, timeline_link=item.timeline_link)
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
    queue.next_retry_at = None
    item.restored_at = utcnow()
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


async def monitor_summary(session: AsyncSession) -> dict[str, int]:
    result = await session.execute(select(IntegrationQueueMessage.status, func.count()).group_by(IntegrationQueueMessage.status))
    counts = {status.value if hasattr(status, "value") else str(status): count for status, count in result.all()}
    dlq_count = await session.scalar(select(func.count()).select_from(DeadLetterQueueItem).where(DeadLetterQueueItem.archived.is_(False)))
    counts["dlq"] = int(dlq_count or counts.get("dlq", 0))
    return counts


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
