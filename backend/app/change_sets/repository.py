from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.change_sets.models import ChangeSet, ChangeSetStatus


async def list_change_sets(session: AsyncSession) -> list[ChangeSet]:
    result = await session.execute(select(ChangeSet).options(selectinload(ChangeSet.items)).order_by(ChangeSet.created_at.desc()))
    return list(result.scalars().unique().all())


async def get_change_set(session: AsyncSession, change_set_id: UUID) -> ChangeSet | None:
    result = await session.execute(select(ChangeSet).options(selectinload(ChangeSet.items)).where(ChangeSet.id == change_set_id).limit(1))
    return result.scalar_one_or_none()


async def pending_count(session: AsyncSession) -> int:
    rows = await list_change_sets(session)
    return len([item for item in rows if item.status in {ChangeSetStatus.DRAFT, ChangeSetStatus.EXPORTED, ChangeSetStatus.IMPORT_PREVIEWED, ChangeSetStatus.FAILED}])


async def last_applied(session: AsyncSession) -> ChangeSet | None:
    result = await session.execute(select(ChangeSet).where(ChangeSet.status == ChangeSetStatus.APPLIED).order_by(ChangeSet.applied_at.desc().nullslast(), ChangeSet.created_at.desc()).limit(1))
    return result.scalar_one_or_none()
