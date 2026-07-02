from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance


async def list_instances(session: AsyncSession) -> list[ConnectorInstance]:
    result = await session.execute(select(ConnectorInstance).order_by(ConnectorInstance.name.asc()))
    return list(result.scalars().all())


async def get_instance(session: AsyncSession, connector_id: UUID) -> ConnectorInstance | None:
    return await session.get(ConnectorInstance, connector_id)


async def get_by_name(session: AsyncSession, name: str) -> ConnectorInstance | None:
    result = await session.execute(select(ConnectorInstance).where(ConnectorInstance.name == name))
    return result.scalar_one_or_none()
