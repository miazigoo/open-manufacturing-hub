from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditEvent


def filtered_query(
    *,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    actor_username: str | None = None,
    category: str | None = None,
    action: str | None = None,
    object_type: str | None = None,
    object_id: str | None = None,
    severity: str | None = None,
    actor_user_id: UUID | None = None,
    search: str | None = None,
):
    query = select(AuditEvent)
    if date_from:
        query = query.where(AuditEvent.timestamp >= date_from)
    if date_to:
        query = query.where(AuditEvent.timestamp <= date_to)
    if actor_username:
        query = query.where(AuditEvent.actor_username.ilike(f"%{actor_username}%"))
    if actor_user_id:
        query = query.where(AuditEvent.actor_user_id == actor_user_id)
    if category:
        query = query.where(AuditEvent.category == category)
    if action:
        query = query.where(AuditEvent.action == action)
    if object_type:
        query = query.where(AuditEvent.object_type == object_type)
    if object_id:
        query = query.where(AuditEvent.object_id == object_id)
    if severity:
        query = query.where(AuditEvent.severity == severity)
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(AuditEvent.summary.ilike(pattern), AuditEvent.action.ilike(pattern), AuditEvent.object_name.ilike(pattern), AuditEvent.request_id.ilike(pattern)))
    return query


async def list_events(session: AsyncSession, *, limit: int = 50, offset: int = 0, **filters) -> tuple[list[AuditEvent], int]:
    base = filtered_query(**filters)
    total = int(await session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    result = await session.execute(base.order_by(AuditEvent.timestamp.desc()).offset(offset).limit(limit))
    return list(result.scalars().all()), total


async def get_event(session: AsyncSession, event_id: UUID) -> AuditEvent | None:
    return await session.get(AuditEvent, event_id)


async def cleanup_before(session: AsyncSession, cutoff: datetime, *, dry_run: bool = False) -> int:
    count = int(await session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.timestamp < cutoff)) or 0)
    if not dry_run and count:
        await session.execute(delete(AuditEvent).where(AuditEvent.timestamp < cutoff))
    return count


async def stats(session: AsyncSession) -> dict:
    total = int(await session.scalar(select(func.count()).select_from(AuditEvent)) or 0)
    by_category_rows = (await session.execute(select(AuditEvent.category, func.count()).group_by(AuditEvent.category))).all()
    by_severity_rows = (await session.execute(select(AuditEvent.severity, func.count()).group_by(AuditEvent.severity))).all()
    oldest = await session.scalar(select(func.min(AuditEvent.timestamp)))
    newest = await session.scalar(select(func.max(AuditEvent.timestamp)))
    return {
        "total": total,
        "by_category": {str(key.value if hasattr(key, "value") else key): int(value) for key, value in by_category_rows},
        "by_severity": {str(key.value if hasattr(key, "value") else key): int(value) for key, value in by_severity_rows},
        "oldest_timestamp": oldest,
        "newest_timestamp": newest,
    }
