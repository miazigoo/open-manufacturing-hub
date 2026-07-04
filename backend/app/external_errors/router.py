from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.external_errors.models import ExternalErrorRecord
from app.external_errors.schemas import ExternalErrorRead, ExternalErrorSummary
from app.external_errors.service import get_external_error_or_404, list_for_event

router = APIRouter(prefix="/api/external-errors", tags=["external-errors"])


@router.get("", response_model=list[ExternalErrorSummary])
async def list_external_errors(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ExternalErrorRecord).order_by(ExternalErrorRecord.created_at.desc()).limit(100))
    return list(result.scalars().all())


@router.get("/event/{event_id}/list", response_model=list[ExternalErrorSummary])
async def list_event_external_errors(event_id: UUID, session: AsyncSession = Depends(get_session)):
    return await list_for_event(session, event_id)


@router.get("/{error_id}", response_model=ExternalErrorRead)
async def get_external_error(error_id: UUID, session: AsyncSession = Depends(get_session)):
    return await get_external_error_or_404(session, error_id)
