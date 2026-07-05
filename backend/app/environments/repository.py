from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.environments.models import EnvironmentProfile, EnvironmentVariable


async def list_environments(session: AsyncSession) -> list[EnvironmentProfile]:
    result = await session.execute(select(EnvironmentProfile).options(selectinload(EnvironmentProfile.variables)).order_by(EnvironmentProfile.is_current.desc(), EnvironmentProfile.environment_type, EnvironmentProfile.name))
    return list(result.scalars().unique().all())


async def get_environment(session: AsyncSession, environment_id: UUID) -> EnvironmentProfile | None:
    result = await session.execute(select(EnvironmentProfile).options(selectinload(EnvironmentProfile.variables)).where(EnvironmentProfile.id == environment_id).limit(1))
    return result.scalar_one_or_none()


async def get_by_code(session: AsyncSession, code: str) -> EnvironmentProfile | None:
    result = await session.execute(select(EnvironmentProfile).options(selectinload(EnvironmentProfile.variables)).where(EnvironmentProfile.code == code).limit(1))
    return result.scalar_one_or_none()


async def current_environment(session: AsyncSession) -> EnvironmentProfile | None:
    result = await session.execute(select(EnvironmentProfile).options(selectinload(EnvironmentProfile.variables)).where(EnvironmentProfile.is_current.is_(True)).limit(1))
    return result.scalar_one_or_none()


async def get_variable(session: AsyncSession, environment_id: UUID, key: str) -> EnvironmentVariable | None:
    result = await session.execute(select(EnvironmentVariable).where(EnvironmentVariable.environment_id == environment_id, EnvironmentVariable.key == key).limit(1))
    return result.scalar_one_or_none()


async def variables_for_environment(session: AsyncSession, environment_id: UUID) -> list[EnvironmentVariable]:
    result = await session.execute(select(EnvironmentVariable).where(EnvironmentVariable.environment_id == environment_id).order_by(EnvironmentVariable.key))
    return list(result.scalars().all())
