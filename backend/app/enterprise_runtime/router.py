from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.enums import EnterpriseQueueStatus
from app.enterprise_runtime import service
from app.enterprise_runtime.schemas import (
    BusinessRuleCreate,
    BusinessRuleRead,
    BusinessRuleRunRequest,
    BusinessRuleRunResponse,
    CanonicalObjectCreate,
    CanonicalObjectRead,
    DLQItemRead,
    MonitorSummary,
    ODataCachePreloadRequest,
    ODataCacheRead,
    QueueMessageCreate,
    QueueEditRetryRequest,
    QueueMessagePatch,
    QueueMessageRead,
    QueueProcessResponse,
    ResolveRequest,
    ResolveResponse,
    ResolverCreate,
    ResolverRead,
    TransformApplyRequest,
    TransformApplyResponse,
)
from app.enterprise_runtime.transforms import list_transforms

router = APIRouter(prefix="/api/enterprise-runtime", tags=["enterprise-runtime"])


@router.post("/install-presets")
async def install_presets(session: AsyncSession = Depends(get_session)):
    result = await service.install_runtime_presets(session)
    await session.commit()
    return result


@router.get("/queue", response_model=list[QueueMessageRead])
async def list_queue(
    status: EnterpriseQueueStatus | None = None,
    business_object: str | None = None,
    operation: str | None = None,
    source_system: str | None = None,
    target_system: str | None = None,
    business_key: str | None = None,
    has_error: bool | None = None,
    sort: str = "priority",
    session: AsyncSession = Depends(get_session),
):
    return await service.list_queue(session, status, business_object, operation, source_system, target_system, business_key, has_error, sort)


@router.get("/queue/{queue_id}", response_model=QueueMessageRead)
async def get_queue(queue_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_queue_or_404(session, queue_id)


@router.post("/queue", response_model=QueueMessageRead)
async def create_queue(request: QueueMessageCreate, session: AsyncSession = Depends(get_session)):
    item = await service.create_queue_message(session, request)
    await session.commit()
    return item


@router.patch("/queue/{queue_id}", response_model=QueueMessageRead)
async def patch_queue(queue_id: UUID, request: QueueMessagePatch, session: AsyncSession = Depends(get_session)):
    item = await service.patch_queue(session, queue_id, request)
    await session.commit()
    return item


@router.post("/queue/{queue_id}/processing", response_model=QueueMessageRead)
async def mark_processing(queue_id: UUID, worker: str = Query(default="manual"), session: AsyncSession = Depends(get_session)):
    item = await service.mark_processing(session, queue_id, worker)
    await session.commit()
    return item


@router.post("/queue/{queue_id}/dlq", response_model=DLQItemRead)
async def move_to_dlq(queue_id: UUID, reason: str = Query(default="Manual DLQ"), session: AsyncSession = Depends(get_session)):
    item = await service.move_to_dlq(session, queue_id, reason)
    await session.commit()
    return item


@router.post("/queue/{queue_id}/retry-now", response_model=QueueMessageRead)
async def retry_now(queue_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.retry_now(session, queue_id)
    await session.commit()
    return item


@router.post("/queue/{queue_id}/cancel", response_model=QueueMessageRead)
async def cancel_queue(queue_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.cancel_queue(session, queue_id)
    await session.commit()
    return item


@router.post("/queue/{queue_id}/force-complete", response_model=QueueMessageRead)
async def force_complete(queue_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.force_complete_queue(session, queue_id)
    await session.commit()
    return item


@router.post("/queue/{queue_id}/unlock", response_model=QueueMessageRead)
async def unlock_queue(queue_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.unlock_queue(session, queue_id)
    await session.commit()
    return item


@router.post("/queue/process-once", response_model=QueueProcessResponse)
async def process_once(worker: str = Query(default="api-manual"), session: AsyncSession = Depends(get_session)):
    item = await service.process_once(session, worker)
    await session.commit()
    items = [item] if item else []
    return _process_response(items)


@router.post("/queue/process-batch", response_model=QueueProcessResponse)
async def process_batch(limit: int = Query(default=10, ge=1, le=100), worker: str = Query(default="api-manual"), session: AsyncSession = Depends(get_session)):
    items = await service.process_batch(session, limit=limit, worker=worker)
    await session.commit()
    return _process_response(items)


@router.get("/dlq", response_model=list[DLQItemRead])
async def list_dlq(include_archived: bool = False, session: AsyncSession = Depends(get_session)):
    return await service.list_dlq(session, include_archived)


@router.get("/dlq/{item_id}", response_model=DLQItemRead)
async def get_dlq(item_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_dlq_or_404(session, item_id)


@router.post("/dlq/{item_id}/retry", response_model=QueueMessageRead)
async def retry_dlq(item_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.retry_dlq(session, item_id)
    await session.commit()
    return item


@router.post("/dlq/{item_id}/edit-and-retry", response_model=QueueMessageRead)
async def edit_retry_dlq(item_id: UUID, request: QueueEditRetryRequest, session: AsyncSession = Depends(get_session)):
    item = await service.edit_retry_dlq(session, item_id, request.payload_json)
    await session.commit()
    return item


@router.post("/dlq/{item_id}/cancel", response_model=DLQItemRead)
async def cancel_dlq(item_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.archive_dlq(session, item_id)
    await session.commit()
    return item


@router.post("/dlq/{item_id}/force-complete", response_model=QueueMessageRead)
async def force_complete_dlq(item_id: UUID, session: AsyncSession = Depends(get_session)):
    queue = await service.retry_dlq(session, item_id)
    queue = await service.force_complete_queue(session, queue.id)
    await session.commit()
    return queue


@router.post("/dlq/{item_id}/restore", response_model=QueueMessageRead)
async def restore_dlq(item_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.retry_dlq(session, item_id)
    await session.commit()
    return item


@router.post("/dlq/{item_id}/replay")
async def replay_dlq(item_id: UUID, session: AsyncSession = Depends(get_session)):
    run = await service.replay_dlq(session, item_id)
    await session.commit()
    return run


@router.post("/dlq/{item_id}/archive", response_model=DLQItemRead)
async def archive_dlq(item_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.archive_dlq(session, item_id)
    await session.commit()
    return item


@router.get("/monitor", response_model=MonitorSummary)
async def monitor(session: AsyncSession = Depends(get_session)):
    counts = await service.monitor_summary(session)
    return MonitorSummary(**counts)


@router.get("/worker-health")
async def worker_health(session: AsyncSession = Depends(get_session)):
    return await service.worker_health(session)


@router.get("/canonical-objects", response_model=list[CanonicalObjectRead])
async def list_canonical_objects(session: AsyncSession = Depends(get_session)):
    return await service.list_canonical_objects(session)


@router.post("/canonical-objects", response_model=CanonicalObjectRead)
async def upsert_canonical_object(request: CanonicalObjectCreate, session: AsyncSession = Depends(get_session)):
    item = await service.upsert_canonical_object(session, request)
    await session.commit()
    return item


@router.get("/resolvers", response_model=list[ResolverRead])
async def list_resolvers(session: AsyncSession = Depends(get_session)):
    return await service.list_resolvers(session)


@router.post("/resolvers", response_model=ResolverRead)
async def upsert_resolver(request: ResolverCreate, session: AsyncSession = Depends(get_session)):
    item = await service.upsert_resolver(session, request)
    await session.commit()
    return item


@router.post("/resolvers/{resolver_id}/resolve", response_model=ResolveResponse)
async def resolve(resolver_id: UUID, request: ResolveRequest, session: AsyncSession = Depends(get_session)):
    result = await service.resolve(session, resolver_id, request.input, request.lookup_key, request.use_cache)
    await session.commit()
    return result


@router.get("/transforms")
async def transforms():
    return list_transforms()


@router.post("/transforms/apply", response_model=TransformApplyResponse)
async def apply_transform(request: TransformApplyRequest):
    result = await service.apply_transform_by_name(request.name, request.value, request.params)
    return TransformApplyResponse(name=request.name, result=result)


@router.get("/business-rules", response_model=list[BusinessRuleRead])
async def list_business_rules(session: AsyncSession = Depends(get_session)):
    return await service.list_rules(session)


@router.post("/business-rules", response_model=BusinessRuleRead)
async def upsert_business_rule(request: BusinessRuleCreate, session: AsyncSession = Depends(get_session)):
    item = await service.upsert_rule(session, request)
    await session.commit()
    return item


@router.post("/business-rules/{rule_id}/run", response_model=BusinessRuleRunResponse)
async def run_business_rule(rule_id: UUID, request: BusinessRuleRunRequest, session: AsyncSession = Depends(get_session)):
    return await service.run_rule(session, rule_id, request.payload)


@router.get("/odata-cache", response_model=list[ODataCacheRead])
async def list_cache(session: AsyncSession = Depends(get_session)):
    return await service.list_cache(session)


@router.post("/odata-cache/preload", response_model=ODataCacheRead)
async def preload_cache(request: ODataCachePreloadRequest, session: AsyncSession = Depends(get_session)):
    item = await service.preload_cache(session, request.resolver_name, request.lookup_key, request.value_json, request.ttl_seconds)
    await session.commit()
    return item


@router.post("/odata-cache/{cache_id}/invalidate", response_model=ODataCacheRead)
async def invalidate_cache(cache_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.invalidate_cache(session, cache_id)
    await session.commit()
    return item


def _process_response(items):
    counts = {"completed": 0, "retry_waiting": 0, "dlq": 0, "failed": 0}
    for item in items:
        value = item.status.value if hasattr(item.status, "value") else str(item.status)
        if value in counts:
            counts[value] += 1
    return QueueProcessResponse(processed=len(items), items=items, **counts)


queue_router = APIRouter(prefix="/api/queue", tags=["queue"])
dlq_router = APIRouter(prefix="/api/dlq", tags=["dlq"])


@queue_router.get("", response_model=list[QueueMessageRead])
async def queue_list_alias(status: EnterpriseQueueStatus | None = None, business_object: str | None = None, operation: str | None = None, source_system: str | None = None, target_system: str | None = None, business_key: str | None = None, has_error: bool | None = None, sort: str = "priority", session: AsyncSession = Depends(get_session)):
    return await service.list_queue(session, status, business_object, operation, source_system, target_system, business_key, has_error, sort)


@queue_router.get("/{queue_id}", response_model=QueueMessageRead)
async def queue_get_alias(queue_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_queue_or_404(session, queue_id)


@queue_router.post("", response_model=QueueMessageRead)
async def queue_create_alias(request: QueueMessageCreate, session: AsyncSession = Depends(get_session)):
    item = await service.create_queue_message(session, request)
    await session.commit()
    return item


@queue_router.post("/process-once", response_model=QueueProcessResponse)
async def queue_process_once_alias(worker: str = Query(default="api-manual"), session: AsyncSession = Depends(get_session)):
    item = await service.process_once(session, worker)
    await session.commit()
    return _process_response([item] if item else [])


@queue_router.post("/process-batch", response_model=QueueProcessResponse)
async def queue_process_batch_alias(limit: int = Query(default=10, ge=1, le=100), worker: str = Query(default="api-manual"), session: AsyncSession = Depends(get_session)):
    items = await service.process_batch(session, limit=limit, worker=worker)
    await session.commit()
    return _process_response(items)


@queue_router.post("/{queue_id}/retry-now", response_model=QueueMessageRead)
async def queue_retry_now_alias(queue_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.retry_now(session, queue_id)
    await session.commit()
    return item


@queue_router.post("/{queue_id}/cancel", response_model=QueueMessageRead)
async def queue_cancel_alias(queue_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.cancel_queue(session, queue_id)
    await session.commit()
    return item


@queue_router.post("/{queue_id}/move-to-dlq", response_model=DLQItemRead)
async def queue_move_dlq_alias(queue_id: UUID, reason: str = Query(default="Manual DLQ"), session: AsyncSession = Depends(get_session)):
    item = await service.move_to_dlq(session, queue_id, reason)
    await session.commit()
    return item


@queue_router.post("/{queue_id}/force-complete", response_model=QueueMessageRead)
async def queue_force_complete_alias(queue_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.force_complete_queue(session, queue_id)
    await session.commit()
    return item


@queue_router.post("/{queue_id}/unlock", response_model=QueueMessageRead)
async def queue_unlock_alias(queue_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.unlock_queue(session, queue_id)
    await session.commit()
    return item


@dlq_router.get("", response_model=list[DLQItemRead])
async def dlq_list_alias(include_archived: bool = False, session: AsyncSession = Depends(get_session)):
    return await service.list_dlq(session, include_archived)


@dlq_router.get("/{item_id}", response_model=DLQItemRead)
async def dlq_get_alias(item_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_dlq_or_404(session, item_id)


@dlq_router.post("/{item_id}/retry", response_model=QueueMessageRead)
async def dlq_retry_alias(item_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.retry_dlq(session, item_id)
    await session.commit()
    return item


@dlq_router.post("/{item_id}/edit-and-retry", response_model=QueueMessageRead)
async def dlq_edit_retry_alias(item_id: UUID, request: QueueEditRetryRequest, session: AsyncSession = Depends(get_session)):
    item = await service.edit_retry_dlq(session, item_id, request.payload_json)
    await session.commit()
    return item


@dlq_router.post("/{item_id}/archive", response_model=DLQItemRead)
async def dlq_archive_alias(item_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.archive_dlq(session, item_id)
    await session.commit()
    return item


@dlq_router.post("/{item_id}/cancel", response_model=DLQItemRead)
async def dlq_cancel_alias(item_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.archive_dlq(session, item_id)
    await session.commit()
    return item


@dlq_router.post("/{item_id}/force-complete", response_model=QueueMessageRead)
async def dlq_force_complete_alias(item_id: UUID, session: AsyncSession = Depends(get_session)):
    queue = await service.retry_dlq(session, item_id)
    queue = await service.force_complete_queue(session, queue.id)
    await session.commit()
    return queue
