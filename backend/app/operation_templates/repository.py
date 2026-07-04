from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.operation_templates.models import OperationTemplate


async def list_templates(session: AsyncSession) -> list[OperationTemplate]:
    result = await session.execute(select(OperationTemplate).order_by(OperationTemplate.system_type, OperationTemplate.operation, OperationTemplate.name))
    return list(result.scalars().all())


async def get_template(session: AsyncSession, template_id: UUID) -> OperationTemplate | None:
    return await session.get(OperationTemplate, template_id)


async def get_by_name(session: AsyncSession, name: str) -> OperationTemplate | None:
    result = await session.execute(select(OperationTemplate).where(OperationTemplate.name == name))
    return result.scalar_one_or_none()
