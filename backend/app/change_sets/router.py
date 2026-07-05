from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.change_sets import service
from app.change_sets.schemas import ChangeSetExport, ChangeSetFromDraftsRequest, ChangeSetImportApplyRequest, ChangeSetImportApplyResponse, ChangeSetImportPreview, ChangeSetImportPreviewRequest, ChangeSetRead, ChangeSetSmokeResult
from app.core.database import get_session

router = APIRouter(prefix="/api/change-sets", tags=["change-sets"])


@router.get("", response_model=list[ChangeSetRead])
async def list_change_sets(session: AsyncSession = Depends(get_session)):
    return await service.list_change_sets(session)


@router.get("/{change_set_id}", response_model=ChangeSetRead)
async def get_change_set(change_set_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_change_set_or_404(session, change_set_id)


@router.post("/from-drafts", response_model=ChangeSetRead)
async def create_from_drafts(payload: ChangeSetFromDraftsRequest, request: Request, session: AsyncSession = Depends(get_session)):
    item = await service.create_from_drafts(session, payload, http_request=request)
    await session.commit()
    return item


@router.get("/{change_set_id}/export", response_model=ChangeSetExport)
async def export_change_set(change_set_id: UUID, request: Request, session: AsyncSession = Depends(get_session)):
    payload = await service.export_change_set(session, change_set_id, http_request=request)
    await session.commit()
    return payload


@router.post("/import/preview", response_model=ChangeSetImportPreview)
async def import_preview(payload: ChangeSetImportPreviewRequest, request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.import_preview(session, payload, http_request=request)
    await session.commit()
    return result


@router.post("/import/apply", response_model=ChangeSetImportApplyResponse)
async def import_apply(payload: ChangeSetImportApplyRequest, request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.import_apply(session, payload, http_request=request)
    await session.commit()
    return result


@router.post("/{change_set_id}/run-smoke-tests", response_model=ChangeSetSmokeResult)
async def run_smoke_tests(change_set_id: UUID, request: Request, session: AsyncSession = Depends(get_session)):
    result = await service.run_smoke_tests(session, change_set_id, http_request=request)
    await session.commit()
    return result
