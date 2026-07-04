from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integration_flows.models import IntegrationFlow


async def list_flows(session: AsyncSession) -> list[IntegrationFlow]:
    result = await session.execute(select(IntegrationFlow).order_by(IntegrationFlow.name))
    return list(result.scalars().all())


async def get_flow(session: AsyncSession, flow_id: UUID) -> IntegrationFlow | None:
    return await session.get(IntegrationFlow, flow_id)


async def get_by_slug(session: AsyncSession, slug: str) -> IntegrationFlow | None:
    result = await session.execute(select(IntegrationFlow).where(IntegrationFlow.slug == slug))
    return result.scalar_one_or_none()
