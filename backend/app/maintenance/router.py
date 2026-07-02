from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import NotFoundError
from app.maintenance import repository, service
from app.maintenance.schemas import MaintenanceWindowCreate, MaintenanceWindowPatch, MaintenanceWindowRead

router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


@router.get("", response_model=list[MaintenanceWindowRead])
async def list_maintenance(session: AsyncSession = Depends(get_session)):
    return await repository.list_windows(session)


@router.post("", response_model=MaintenanceWindowRead)
async def create_maintenance(request: MaintenanceWindowCreate, session: AsyncSession = Depends(get_session)):
    window = await service.create_window(session, request)
    await session.commit()
    return window


@router.patch("/{window_id}", response_model=MaintenanceWindowRead)
async def patch_maintenance(window_id: UUID, request: MaintenanceWindowPatch, session: AsyncSession = Depends(get_session)):
    window = await service.patch_window(session, window_id, request)
    await session.commit()
    return window


@router.delete("/{window_id}", status_code=204)
async def delete_maintenance(window_id: UUID, session: AsyncSession = Depends(get_session)):
    window = await repository.get_window(session, window_id)
    if window is None:
        raise NotFoundError("Maintenance window not found")
    await session.delete(window)
    await session.commit()
    return Response(status_code=204)
