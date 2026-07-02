from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.maintenance.models import MaintenanceWindow
from app.maintenance.repository import active_for_component, get_window
from app.maintenance.schemas import MaintenanceWindowCreate, MaintenanceWindowPatch


async def create_window(session: AsyncSession, request: MaintenanceWindowCreate) -> MaintenanceWindow:
    window = MaintenanceWindow(**request.model_dump())
    session.add(window)
    await session.flush()
    return window


async def patch_window(session: AsyncSession, window_id: UUID, request: MaintenanceWindowPatch) -> MaintenanceWindow:
    window = await get_window(session, window_id)
    if window is None:
        raise NotFoundError("Maintenance window not found")
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(window, key, value)
    await session.flush()
    return window


async def active_target_maintenance(session: AsyncSession, target_system: str | None) -> MaintenanceWindow | None:
    if not target_system:
        return None
    return await active_for_component(session, "connector", target_system, datetime.now(timezone.utc))
