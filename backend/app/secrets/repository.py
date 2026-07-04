from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.secrets.models import Secret


async def list_secrets(session: AsyncSession) -> list[Secret]:
    result = await session.execute(select(Secret).order_by(Secret.created_at.desc()))
    return list(result.scalars().all())


async def get_secret(session: AsyncSession, secret_id: UUID) -> Secret | None:
    return await session.get(Secret, secret_id)


async def get_by_name(session: AsyncSession, name: str) -> Secret | None:
    result = await session.execute(select(Secret).where(Secret.name == name))
    return result.scalar_one_or_none()
