from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.onec_workbench.models import IntegrationMessage


async def list_messages(
    session: AsyncSession,
    limit: int = 100,
    offset: int = 0,
) -> list[IntegrationMessage]:
    stmt = (
        select(IntegrationMessage)
        .options(defer(IntegrationMessage.payload_text), defer(IntegrationMessage.payload_json))
        .order_by(IntegrationMessage.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_message(session: AsyncSession, message_id: UUID) -> IntegrationMessage | None:
    return await session.get(IntegrationMessage, message_id)
