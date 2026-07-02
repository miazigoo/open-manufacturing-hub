from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.health import repository, service
from app.health.schemas import AgentHeartbeatCreate, AgentHeartbeatRead, HealthCheckCreate, HealthCheckRead

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health_check():
    return {"status": "ok"}


@router.get("/dashboard")
async def health_dashboard(session: AsyncSession = Depends(get_session)):
    return await service.dashboard(session)


@router.get("/components", response_model=list[HealthCheckRead])
async def components(session: AsyncSession = Depends(get_session)):
    return await repository.latest_checks(session)


@router.post("/checks", response_model=HealthCheckRead)
async def create_check(request: HealthCheckCreate, session: AsyncSession = Depends(get_session)):
    check = await service.create_check(session, request)
    await session.commit()
    return check


@router.post("/agent-heartbeat", response_model=AgentHeartbeatRead)
async def agent_heartbeat(request: AgentHeartbeatCreate, session: AsyncSession = Depends(get_session)):
    heartbeat = await service.record_heartbeat(session, request)
    await session.commit()
    return heartbeat
