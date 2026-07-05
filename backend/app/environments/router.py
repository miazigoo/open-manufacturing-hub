from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.environments import service
from app.environments.schemas import EnvironmentCreate, EnvironmentPatch, EnvironmentRead, EnvironmentVariableCreate, EnvironmentVariablePatch, EnvironmentVariableRead

router = APIRouter(prefix="/api/environments", tags=["environments"])


@router.get("", response_model=list[EnvironmentRead])
async def list_environments(session: AsyncSession = Depends(get_session)):
    return await service.list_environments(session)


@router.post("", response_model=EnvironmentRead)
async def create_environment(payload: EnvironmentCreate, request: Request, session: AsyncSession = Depends(get_session)):
    item = await service.create_environment(session, payload, http_request=request)
    await session.commit()
    return item


@router.get("/current", response_model=EnvironmentRead | None)
async def current_environment(session: AsyncSession = Depends(get_session)):
    return await service.current(session)


@router.get("/{environment_id}", response_model=EnvironmentRead)
async def get_environment(environment_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_environment_or_404(session, environment_id)


@router.patch("/{environment_id}", response_model=EnvironmentRead)
async def patch_environment(environment_id: UUID, payload: EnvironmentPatch, request: Request, session: AsyncSession = Depends(get_session)):
    item = await service.patch_environment(session, environment_id, payload, http_request=request)
    await session.commit()
    return item


@router.post("/{environment_id}/set-current", response_model=EnvironmentRead)
async def set_current(environment_id: UUID, request: Request, session: AsyncSession = Depends(get_session)):
    item = await service.set_current(session, environment_id, http_request=request)
    await session.commit()
    return item


@router.delete("/{environment_id}", status_code=204)
async def delete_environment(environment_id: UUID, request: Request, session: AsyncSession = Depends(get_session)):
    await service.delete_environment(session, environment_id, http_request=request)
    await session.commit()
    return Response(status_code=204)


@router.post("/{environment_id}/variables", response_model=EnvironmentVariableRead)
async def upsert_variable(environment_id: UUID, payload: EnvironmentVariableCreate, request: Request, session: AsyncSession = Depends(get_session)):
    item = await service.upsert_variable(session, environment_id, payload, http_request=request)
    await session.commit()
    return item


@router.patch("/{environment_id}/variables/{key}", response_model=EnvironmentVariableRead)
async def patch_variable(environment_id: UUID, key: str, payload: EnvironmentVariablePatch, request: Request, session: AsyncSession = Depends(get_session)):
    item = await service.patch_variable(session, environment_id, key, payload, http_request=request)
    await session.commit()
    return item


@router.delete("/{environment_id}/variables/{key}", status_code=204)
async def delete_variable(environment_id: UUID, key: str, request: Request, session: AsyncSession = Depends(get_session)):
    await service.delete_variable(session, environment_id, key, http_request=request)
    await session.commit()
    return Response(status_code=204)
