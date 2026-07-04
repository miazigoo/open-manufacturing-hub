from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.onec_workbench.models import IntegrationMessage


async def list_messages(session: AsyncSession) -> list[IntegrationMessage]:
    result = await session.execute(select(IntegrationMessage).order_by(IntegrationMessage.created_at.desc()))
    return list(result.scalars().all())


async def get_message(session: AsyncSession, message_id: UUID) -> IntegrationMessage | None:
    return await session.get(IntegrationMessage, message_id)
