from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import NotFoundError
from app.marking_code_pools.models import MarkingCodePoolExport
from app.marking_code_pools.schemas import (
    MarkingCodePoolActionRetryResponse,
    MarkingCodePoolExportRead,
    MarkingCodePoolExportResponse,
    MarkingCodePoolForwardTestRequest,
    MarkingCodePoolOverview,
    MarkingCodePoolPreviewResponse,
    MarkingCodePoolRoutingRuleCreate,
    MarkingCodePoolRoutingRulePatch,
    MarkingCodePoolRoutingRuleRead,
    MarkingCodePoolSettingsPatch,
    MarkingCodePoolSettingsRead,
    MarkingCodePoolSettingsTestRequest,
    MarkingCodePoolSettingsTestResponse,
    OneCMarkingCodePoolExportRequest,
    RoutingRuleTestRequest,
    RoutingRuleTestResponse,
)
from app.marking_code_pools import routing, service

router = APIRouter(prefix="/api/marking-code-pools", tags=["marking-code-pools"])


@router.post("/onec/export-file", response_model=MarkingCodePoolExportResponse)
async def export_onec_pool_to_file(request: OneCMarkingCodePoolExportRequest, session: AsyncSession = Depends(get_session)):
    record, dnp_forward = await service.export_onec_pool_to_file(session, request)
    await session.commit()
    actions = (record.metadata_json or {}).get("actions", {})
    response_meta = (record.metadata_json or {}).get("response", {})
    segments = (record.metadata_json or {}).get("segments", [])
    if segments:
        total = sum(int(item.get("total_codes") or 0) for item in segments)
        message = f"Accepted {total} marking codes in {len(segments)} segments; status={response_meta.get('status', record.status)}"
    else:
        message = f"Accepted {record.total_codes} marking codes as {record.file_name}; status={record.status}"
    if dnp_forward is not None:
        message += "; external service accepted the pool"
    return MarkingCodePoolExportResponse(
        export=record,
        message=message,
        success=bool(response_meta.get("success", record.status != "failed")),
        status=str(response_meta.get("status", record.status)),
        warnings=list(response_meta.get("warnings") or []),
        actions=actions,
        segments=segments,
        external_forward=dnp_forward,
        dnp_forward=dnp_forward,
    )


@router.post("/onec/export-file/preview", response_model=MarkingCodePoolPreviewResponse)
async def preview_onec_pool_to_file(request: OneCMarkingCodePoolExportRequest, session: AsyncSession = Depends(get_session)):
    return await service.preview_onec_pool_export(session, request)


@router.get("/overview", response_model=MarkingCodePoolOverview)
async def get_overview(session: AsyncSession = Depends(get_session)):
    settings = await service.read_settings(session)
    # Latest export
    latest_res = await session.execute(
        select(MarkingCodePoolExport).order_by(MarkingCodePoolExport.created_at.desc()).limit(1)
    )
    latest = latest_res.scalar_one_or_none()
    
    # 3 latest errors
    errors_res = await session.execute(
        select(MarkingCodePoolExport)
        .where(MarkingCodePoolExport.error_message.is_not(None))
        .order_by(MarkingCodePoolExport.created_at.desc())
        .limit(3)
    )
    errors = list(errors_res.scalars().all())

    from sqlalchemy import func
    total = await session.scalar(select(func.count(MarkingCodePoolExport.id))) or 0

    return MarkingCodePoolOverview(
        settings=settings,
        latest_export=latest,
        recent_errors=errors,
        total_exports=total,
    )


@router.get("/settings", response_model=MarkingCodePoolSettingsRead)
async def get_settings(session: AsyncSession = Depends(get_session)):
    return await service.read_settings(session)


@router.patch("/settings", response_model=MarkingCodePoolSettingsRead)
async def patch_settings(payload: MarkingCodePoolSettingsPatch, session: AsyncSession = Depends(get_session)):
    settings = await service.patch_settings(session, payload)
    await session.commit()
    return settings


@router.post("/settings/test-local-dir", response_model=MarkingCodePoolSettingsTestResponse)
async def test_local_dir(session: AsyncSession = Depends(get_session)):
    return await service.test_local_dir(session)


@router.post("/settings/test-laser-dir", response_model=MarkingCodePoolSettingsTestResponse)
async def test_laser_dir(payload: MarkingCodePoolSettingsTestRequest | None = None, session: AsyncSession = Depends(get_session)):
    payload = payload or MarkingCodePoolSettingsTestRequest()
    return await service.test_laser_dir(session, dry_run=payload.dry_run)


@router.post("/settings/test-forward", response_model=MarkingCodePoolSettingsTestResponse)
async def test_forward(payload: MarkingCodePoolForwardTestRequest | None = None, session: AsyncSession = Depends(get_session)):
    payload = payload or MarkingCodePoolForwardTestRequest()
    return await service.test_forward(session, send_test_request=payload.send_test_request)


@router.get("/routing-rules", response_model=list[MarkingCodePoolRoutingRuleRead])
async def list_routing_rules(session: AsyncSession = Depends(get_session)):
    return await routing.list_rules(session)


@router.post("/routing-rules", response_model=MarkingCodePoolRoutingRuleRead)
async def create_routing_rule(payload: MarkingCodePoolRoutingRuleCreate, session: AsyncSession = Depends(get_session)):
    rule = await routing.create_rule(session, payload)
    await session.commit()
    return rule


@router.post("/routing-rules/test", response_model=RoutingRuleTestResponse)
async def test_routing_rules(payload: RoutingRuleTestRequest, session: AsyncSession = Depends(get_session)):
    return await routing.test_rules(session, payload)


@router.get("/routing-rules/{rule_id}", response_model=MarkingCodePoolRoutingRuleRead)
async def get_routing_rule(rule_id: UUID, session: AsyncSession = Depends(get_session)):
    return await routing.get_rule_or_404(session, rule_id)


@router.patch("/routing-rules/{rule_id}", response_model=MarkingCodePoolRoutingRuleRead)
async def patch_routing_rule(rule_id: UUID, payload: MarkingCodePoolRoutingRulePatch, session: AsyncSession = Depends(get_session)):
    rule = await routing.patch_rule(session, rule_id, payload)
    await session.commit()
    return rule


@router.delete("/routing-rules/{rule_id}", status_code=204)
async def delete_routing_rule(rule_id: UUID, session: AsyncSession = Depends(get_session)):
    await routing.delete_rule(session, rule_id)
    await session.commit()


@router.get("/exports", response_model=list[MarkingCodePoolExportRead])
async def list_exports(
    limit: int = 50,
    cursor: UUID | None = None,
    session: AsyncSession = Depends(get_session),
):
    query = select(MarkingCodePoolExport)
    if cursor is not None:
        cursor_item = await session.get(MarkingCodePoolExport, cursor)
        if cursor_item:
            query = query.where(MarkingCodePoolExport.created_at < cursor_item.created_at)
    query = query.order_by(MarkingCodePoolExport.created_at.desc()).limit(min(limit, 200))
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/exports/{export_id}", response_model=MarkingCodePoolExportRead)
async def get_export(export_id: UUID, session: AsyncSession = Depends(get_session)):
    record = await session.get(MarkingCodePoolExport, export_id)
    if record is None:
        raise NotFoundError("Marking code pool export not found")
    return record


@router.get("/exports/{export_id}/download")
async def download_export(export_id: UUID, session: AsyncSession = Depends(get_session)):
    path, file_name = await service.export_download_path(session, export_id)
    return FileResponse(path, media_type="text/plain", filename=file_name)


@router.post("/exports/{export_id}/retry-forward", response_model=MarkingCodePoolActionRetryResponse)
async def retry_forward(export_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.retry_forward(session, export_id)
    await session.commit()
    return result


@router.post("/exports/{export_id}/retry-laser-copy", response_model=MarkingCodePoolActionRetryResponse)
async def retry_laser_copy(export_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.retry_laser_copy(session, export_id)
    await session.commit()
    return result
