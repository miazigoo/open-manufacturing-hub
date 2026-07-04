from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
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
async def export_config(payload: ExportConfigRequest | None = None, http_request: Request = None, session: AsyncSession = Depends(get_session)):
    _, result_payload = await service.export_config(session, payload or ExportConfigRequest())
    audit_payload = _audit_payload(result_payload)
    await audit_service.record_action(session, request=http_request, action="production.config_exported", category="production", object_type="production_config", summary="Production config export created", details={"export_id": audit_payload.get("export_id"), "file_name": audit_payload.get("file_name"), "size_bytes": audit_payload.get("size_bytes"), "warnings": audit_payload.get("warnings")})
    await session.commit()
    return result_payload


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
async def import_apply(payload: ImportConfigRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.import_apply(session, payload)
    await audit_service.record_action(session, request=http_request, action="production.config_imported", category="production", object_type="production_config", summary="Production config import applied", details={"mode": payload.mode, "result": _audit_payload(result)})
    await session.commit()
    return result


@router.post("/pre-update-check", response_model=UpdateCheckResponse)
async def pre_update_check(http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.pre_update_check(session)
    await audit_service.record_action(session, request=http_request, action="production.pre_update_check", category="production", object_type="production_check", summary="Pre-update check completed", details=_audit_payload(result))
    await session.commit()
    return result


@router.post("/post-update-check", response_model=UpdateCheckResponse)
async def post_update_check(http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.post_update_check(session)
    await audit_service.record_action(session, request=http_request, action="production.post_update_check", category="production", object_type="production_check", summary="Post-update check completed", details=_audit_payload(result))
    await session.commit()
    return result


@router.get("/update-mode", response_model=UpdateModeStatus)
async def update_mode(session: AsyncSession = Depends(get_session)):
    return (await service.worker_status(session))["update_mode"]


@router.post("/update-mode/enable", response_model=UpdateModeStatus)
async def enable_update_mode(payload: UpdateModeRequest | None = None, http_request: Request = None, session: AsyncSession = Depends(get_session)):
    payload = payload or UpdateModeRequest()
    result = await service.enable_update_mode(session, message=payload.message, enabled_by=payload.enabled_by)
    await audit_service.record_action(session, request=http_request, action="production.update_mode_enabled", category="production", object_type="update_mode", summary="Production update mode enabled", details=result)
    await session.commit()
    return result


@router.post("/update-mode/disable", response_model=UpdateModeStatus)
async def disable_update_mode(http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.disable_update_mode(session)
    await audit_service.record_action(session, request=http_request, action="production.update_mode_disabled", category="production", object_type="update_mode", summary="Production update mode disabled", details=result)
    await session.commit()
    return result


@router.post("/workers/pause", response_model=UpdateModeStatus)
async def pause_workers(payload: UpdateModeRequest | None = None, http_request: Request = None, session: AsyncSession = Depends(get_session)):
    payload = payload or UpdateModeRequest(message="Workers paused for maintenance")
    result = await service.enable_update_mode(session, message=payload.message, enabled_by=payload.enabled_by)
    await audit_service.record_action(session, request=http_request, action="production.workers_paused", category="production", object_type="update_mode", summary="Production workers paused", details=result)
    await session.commit()
    return result


@router.post("/workers/resume", response_model=UpdateModeStatus)
async def resume_workers(http_request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.disable_update_mode(session)
    await audit_service.record_action(session, request=http_request, action="production.workers_resumed", category="production", object_type="update_mode", summary="Production workers resumed", details=result)
    await session.commit()
    return result


@router.get("/workers/status")
async def workers_status(session: AsyncSession = Depends(get_session)):
    return await service.worker_status(session)


def _audit_payload(value):
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value
