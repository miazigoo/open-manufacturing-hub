from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.health import readiness, repository, service
from app.health.schemas import AgentHeartbeatCreate, AgentHeartbeatHistoryItem, AgentHeartbeatRead, AgentHeartbeatSummary, HealthCheckCreate, HealthCheckRead

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health_check():
    return {"status": "ok"}


@router.get("/live")
async def health_live():
    return await readiness.live()


@router.get("/ready")
async def health_ready(session: AsyncSession = Depends(get_session)):
    return await readiness.ready(session)


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


@router.get("/agents", response_model=list[AgentHeartbeatSummary])
async def agents(session: AsyncSession = Depends(get_session)):
    return await service.agent_summaries(session)


@router.get("/agent-heartbeats", response_model=list[AgentHeartbeatHistoryItem])
async def agent_heartbeats(limit: int = 100, site_code: str | None = None, session: AsyncSession = Depends(get_session)):
    return await service.agent_history(session, limit=limit, site_code=site_code)
