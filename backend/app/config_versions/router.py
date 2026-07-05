from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_versions import service
from app.config_versions.schemas import (
    ConfigDiffResponse,
    ConfigDraftPatch,
    ConfigDraftRequest,
    ConfigPublishRequest,
    ConfigRollbackRequest,
    ConfigVersionRead,
    ConfigVersionsResponse,
    ConfigVersionTestRequest,
    ConfigVersionTestResponse,
)
from app.core.database import get_session

router = APIRouter(prefix="/api/config", tags=["config-versions"])


@router.get("/{object_type}/{object_id}/versions", response_model=ConfigVersionsResponse)
async def list_versions(object_type: str, object_id: UUID, session: AsyncSession = Depends(get_session)):
    result = await service.versions(session, object_type, object_id)
    await session.commit()
    return result


@router.get("/{object_type}/{object_id}/versions/{version_id}", response_model=ConfigVersionRead)
async def get_version(object_type: str, object_id: UUID, version_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_version_or_404(session, object_type, object_id, version_id)


@router.post("/{object_type}/{object_id}/draft", response_model=ConfigVersionRead)
async def create_draft(object_type: str, object_id: UUID, payload: ConfigDraftRequest, request: Request, session: AsyncSession = Depends(get_session)):
    version = await service.create_or_update_draft(session, object_type, object_id, payload, http_request=request)
    await session.commit()
    return version


@router.patch("/{object_type}/{object_id}/draft", response_model=ConfigVersionRead)
async def patch_draft(object_type: str, object_id: UUID, payload: ConfigDraftPatch, request: Request, session: AsyncSession = Depends(get_session)):
    version = await service.patch_draft(session, object_type, object_id, payload, http_request=request)
    await session.commit()
    return version


@router.delete("/{object_type}/{object_id}/draft", status_code=204)
async def discard_draft(object_type: str, object_id: UUID, request: Request, session: AsyncSession = Depends(get_session)):
    await service.discard_draft(session, object_type, object_id, http_request=request)
    await session.commit()
    return Response(status_code=204)


@router.post("/{object_type}/{object_id}/publish", response_model=ConfigVersionRead)
async def publish(object_type: str, object_id: UUID, payload: ConfigPublishRequest, request: Request, session: AsyncSession = Depends(get_session)):
    version = await service.publish(session, object_type, object_id, payload, http_request=request)
    await session.commit()
    return version


@router.post("/{object_type}/{object_id}/rollback", response_model=ConfigVersionRead)
async def rollback(object_type: str, object_id: UUID, payload: ConfigRollbackRequest, request: Request, session: AsyncSession = Depends(get_session)):
    version = await service.rollback(session, object_type, object_id, payload, http_request=request)
    await session.commit()
    return version


@router.get("/{object_type}/{object_id}/diff", response_model=ConfigDiffResponse)
async def diff_versions(object_type: str, object_id: UUID, from_version: UUID = Query(...), to_version: UUID = Query(...), session: AsyncSession = Depends(get_session)):
    return await service.diff_versions(session, object_type, object_id, from_version, to_version)


@router.post("/{object_type}/{object_id}/versions/{version_id}/test", response_model=ConfigVersionTestResponse)
async def test_version(object_type: str, object_id: UUID, version_id: UUID, payload: ConfigVersionTestRequest, request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.test_version(session, object_type, object_id, version_id, payload, http_request=request)
    await session.commit()
    return result
