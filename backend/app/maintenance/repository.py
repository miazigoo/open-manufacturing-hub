from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.maintenance.models import MaintenanceWindow


async def list_windows(session: AsyncSession) -> list[MaintenanceWindow]:
    result = await session.execute(select(MaintenanceWindow).order_by(MaintenanceWindow.starts_at.desc()))
    return list(result.scalars().all())


async def get_window(session: AsyncSession, window_id: UUID) -> MaintenanceWindow | None:
    return await session.get(MaintenanceWindow, window_id)


async def active_for_component(session: AsyncSession, component_type: str, component_name: str, at: datetime) -> MaintenanceWindow | None:
    result = await session.execute(
        select(MaintenanceWindow).where(
            MaintenanceWindow.enabled.is_(True),
            MaintenanceWindow.component_type == component_type,
            MaintenanceWindow.component_name == component_name,
            MaintenanceWindow.starts_at <= at,
            MaintenanceWindow.ends_at >= at,
        ).limit(1)
    )
    return result.scalar_one_or_none()
