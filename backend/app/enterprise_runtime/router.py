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
    QueueMessagePatch,
    QueueMessageRead,
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
async def list_queue(status: EnterpriseQueueStatus | None = None, business_object: str | None = None, operation: str | None = None, session: AsyncSession = Depends(get_session)):
    return await service.list_queue(session, status, business_object, operation)


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


@router.get("/dlq", response_model=list[DLQItemRead])
async def list_dlq(include_archived: bool = False, session: AsyncSession = Depends(get_session)):
    return await service.list_dlq(session, include_archived)


@router.post("/dlq/{item_id}/retry", response_model=QueueMessageRead)
async def retry_dlq(item_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await service.retry_dlq(session, item_id)
    await session.commit()
    return item


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
