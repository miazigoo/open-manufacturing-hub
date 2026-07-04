from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import NotFoundError
from app.production import backups, service
from app.production.schemas import BackupRecordRead, ExportConfigRequest, ExportConfigResponse, ImportApplyResponse, ImportConfigRequest, ImportPreview, ProductionStatus, SystemSnapshot, UpdateCheckResponse, UpdateModeRequest, UpdateModeStatus

router = APIRouter(prefix="/api/production", tags=["production"])


@router.get("/status", response_model=ProductionStatus)
async def production_status(session: AsyncSession = Depends(get_session)):
    return await service.status(session)


@router.get("/snapshot", response_model=SystemSnapshot)
async def production_snapshot(session: AsyncSession = Depends(get_session)):
    return await service.snapshot(session)


@router.post("/export-config", response_model=ExportConfigResponse)
async def export_config(request: ExportConfigRequest | None = None, session: AsyncSession = Depends(get_session)):
    _, payload = await service.export_config(session, request or ExportConfigRequest())
    await session.commit()
    return payload


@router.get("/exports", response_model=list[BackupRecordRead])
async def exports(session: AsyncSession = Depends(get_session)):
    return await backups.list_records(session)


@router.get("/exports/{export_id}/download")
async def download_export(export_id: UUID, session: AsyncSession = Depends(get_session)):
    record = await backups.get_record(session, export_id)
    path = service.export_path(record)
    if not path.exists():
        raise NotFoundError("Export file not found")
    return FileResponse(path, media_type="application/json", filename=path.name)


@router.post("/import-config/preview", response_model=ImportPreview)
async def import_preview(request: ImportConfigRequest, session: AsyncSession = Depends(get_session)):
    return await service.import_preview(session, request)


@router.post("/import-config/apply", response_model=ImportApplyResponse)
async def import_apply(request: ImportConfigRequest, session: AsyncSession = Depends(get_session)):
    result = await service.import_apply(session, request)
    await session.commit()
    return result


@router.post("/pre-update-check", response_model=UpdateCheckResponse)
async def pre_update_check(session: AsyncSession = Depends(get_session)):
    return await service.pre_update_check(session)


@router.post("/post-update-check", response_model=UpdateCheckResponse)
async def post_update_check(session: AsyncSession = Depends(get_session)):
    return await service.post_update_check(session)


@router.get("/update-mode", response_model=UpdateModeStatus)
async def update_mode(session: AsyncSession = Depends(get_session)):
    return (await service.worker_status(session))["update_mode"]


@router.post("/update-mode/enable", response_model=UpdateModeStatus)
async def enable_update_mode(request: UpdateModeRequest | None = None, session: AsyncSession = Depends(get_session)):
    payload = request or UpdateModeRequest()
    result = await service.enable_update_mode(session, message=payload.message, enabled_by=payload.enabled_by)
    await session.commit()
    return result


@router.post("/update-mode/disable", response_model=UpdateModeStatus)
async def disable_update_mode(session: AsyncSession = Depends(get_session)):
    result = await service.disable_update_mode(session)
    await session.commit()
    return result


@router.post("/workers/pause", response_model=UpdateModeStatus)
async def pause_workers(request: UpdateModeRequest | None = None, session: AsyncSession = Depends(get_session)):
    payload = request or UpdateModeRequest(message="Workers paused for maintenance")
    result = await service.enable_update_mode(session, message=payload.message, enabled_by=payload.enabled_by)
    await session.commit()
    return result


@router.post("/workers/resume", response_model=UpdateModeStatus)
async def resume_workers(session: AsyncSession = Depends(get_session)):
    result = await service.disable_update_mode(session)
    await session.commit()
    return result


@router.get("/workers/status")
async def workers_status(session: AsyncSession = Depends(get_session)):
    return await service.worker_status(session)
