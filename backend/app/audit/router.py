from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import repository, service
from app.audit.schemas import AuditCleanupRequest, AuditCleanupResponse, AuditEventRead, AuditListResponse, AuditStats
from app.core.database import get_session
from app.core.errors import NotFoundError

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=AuditListResponse)
async def list_audit_events(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    actor_username: str | None = None,
    category: str | None = None,
    action: str | None = None,
    object_type: str | None = None,
    object_id: str | None = None,
    severity: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    items, total = await repository.list_events(
        session,
        limit=limit,
        offset=offset,
        date_from=date_from,
        date_to=date_to,
        actor_username=actor_username,
        category=category,
        action=action,
        object_type=object_type,
        object_id=object_id,
        severity=severity,
        search=search,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/export")
async def export_audit_events(session: AsyncSession = Depends(get_session)):
    items, total = await repository.list_events(session, limit=5000, offset=0)
    return {"total": total, "items": [AuditEventRead.model_validate(item).model_dump(mode="json") for item in items]}


@router.post("/cleanup", response_model=AuditCleanupResponse)
async def cleanup_audit(payload: AuditCleanupRequest | None = None, session: AsyncSession = Depends(get_session)):
    result = await service.cleanup(session, retention_days=(payload.retention_days if payload else None), dry_run=bool(payload and payload.dry_run))
    await session.commit()
    return result


@router.get("/stats", response_model=AuditStats)
async def audit_stats(session: AsyncSession = Depends(get_session)):
    return await repository.stats(session)


@router.get("/object/{object_type}/{object_id}", response_model=AuditListResponse)
async def object_history(object_type: str, object_id: str, limit: int = Query(default=50, ge=1, le=500), offset: int = Query(default=0, ge=0), session: AsyncSession = Depends(get_session)):
    items, total = await repository.list_events(session, object_type=object_type, object_id=object_id, limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/user/{user_id}", response_model=AuditListResponse)
async def user_history(user_id: UUID, limit: int = Query(default=50, ge=1, le=500), offset: int = Query(default=0, ge=0), session: AsyncSession = Depends(get_session)):
    items, total = await repository.list_events(session, actor_user_id=user_id, limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{audit_event_id}", response_model=AuditEventRead)
async def get_audit_event(audit_event_id: UUID, session: AsyncSession = Depends(get_session)):
    item = await repository.get_event(session, audit_event_id)
    if item is None:
        raise NotFoundError("Audit event not found")
    return item
