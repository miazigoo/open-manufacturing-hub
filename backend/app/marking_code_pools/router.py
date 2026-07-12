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
    MarkingCodePoolPreviewResponse,
    MarkingCodePoolSettingsPatch,
    MarkingCodePoolSettingsRead,
    MarkingCodePoolSettingsTestRequest,
    MarkingCodePoolSettingsTestResponse,
    OneCMarkingCodePoolExportRequest,
)
from app.marking_code_pools import service

router = APIRouter(prefix="/api/marking-code-pools", tags=["marking-code-pools"])


@router.post("/onec/export-file", response_model=MarkingCodePoolExportResponse)
async def export_onec_pool_to_file(request: OneCMarkingCodePoolExportRequest, session: AsyncSession = Depends(get_session)):
    record, dnp_forward = await service.export_onec_pool_to_file(session, request)
    await session.commit()
    actions = (record.metadata_json or {}).get("actions", {})
    response_meta = (record.metadata_json or {}).get("response", {})
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
        external_forward=dnp_forward,
        dnp_forward=dnp_forward,
    )


@router.post("/onec/export-file/preview", response_model=MarkingCodePoolPreviewResponse)
async def preview_onec_pool_to_file(request: OneCMarkingCodePoolExportRequest, session: AsyncSession = Depends(get_session)):
    return await service.preview_onec_pool_export(session, request)


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


@router.get("/exports", response_model=list[MarkingCodePoolExportRead])
async def list_exports(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(MarkingCodePoolExport).order_by(MarkingCodePoolExport.created_at.desc()).limit(100))
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
