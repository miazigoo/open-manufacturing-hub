from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config_versions.models import ConfigVersion, ConfigVersionStatus

EFFECTIVE_ACTIVE = {ConfigVersionStatus.ACTIVE, ConfigVersionStatus.ROLLBACK}


async def list_versions(session: AsyncSession, object_type: str, object_id: UUID) -> list[ConfigVersion]:
    result = await session.execute(
        select(ConfigVersion)
        .where(ConfigVersion.object_type == object_type, ConfigVersion.object_id == object_id)
        .order_by(ConfigVersion.version_number.desc(), ConfigVersion.created_at.desc())
    )
    return list(result.scalars().all())


async def get_version(session: AsyncSession, version_id: UUID) -> ConfigVersion | None:
    return await session.get(ConfigVersion, version_id)


async def get_active(session: AsyncSession, object_type: str, object_id: UUID) -> ConfigVersion | None:
    result = await session.execute(
        select(ConfigVersion)
        .where(ConfigVersion.object_type == object_type, ConfigVersion.object_id == object_id, ConfigVersion.status.in_(EFFECTIVE_ACTIVE))
        .order_by(ConfigVersion.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_draft(session: AsyncSession, object_type: str, object_id: UUID) -> ConfigVersion | None:
    result = await session.execute(
        select(ConfigVersion)
        .where(ConfigVersion.object_type == object_type, ConfigVersion.object_id == object_id, ConfigVersion.status == ConfigVersionStatus.DRAFT)
        .order_by(ConfigVersion.version_number.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def next_version_number(session: AsyncSession, object_type: str, object_id: UUID) -> int:
    value = await session.scalar(select(func.max(ConfigVersion.version_number)).where(ConfigVersion.object_type == object_type, ConfigVersion.object_id == object_id))
    return int(value or 0) + 1
