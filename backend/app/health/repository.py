from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.health.models import AgentHeartbeat, HealthCheck, Site


async def get_site_by_code(session: AsyncSession, code: str) -> Site | None:
    result = await session.execute(select(Site).where(Site.code == code).options(lazyload(Site.checks)))
    return result.scalar_one_or_none()


async def get_site_by_name(session: AsyncSession, name: str) -> Site | None:
    result = await session.execute(select(Site).where(Site.name == name).options(lazyload(Site.checks)))
    return result.scalar_one_or_none()


async def latest_checks(session: AsyncSession) -> list[HealthCheck]:
    # health_checks grows fast (several rows per heartbeat); dedupe in SQL via a
    # group-by-max subquery instead of loading the whole table into Python.
    latest_timestamps = (
        select(
            HealthCheck.component_type.label("component_type"),
            HealthCheck.component_name.label("component_name"),
            HealthCheck.site_id.label("site_id"),
            func.max(HealthCheck.checked_at).label("max_checked_at"),
        )
        .group_by(HealthCheck.component_type, HealthCheck.component_name, HealthCheck.site_id)
        .subquery()
    )
    result = await session.execute(
        select(HealthCheck).join(
            latest_timestamps,
            (HealthCheck.component_type == latest_timestamps.c.component_type)
            & (HealthCheck.component_name == latest_timestamps.c.component_name)
            & (HealthCheck.checked_at == latest_timestamps.c.max_checked_at)
            & (
                (HealthCheck.site_id == latest_timestamps.c.site_id)
                | (HealthCheck.site_id.is_(None) & latest_timestamps.c.site_id.is_(None))
            ),
        )
    )
    return list(result.scalars().all())


async def list_agent_heartbeats(session: AsyncSession, limit: int = 100, site_code: str | None = None) -> list[tuple[AgentHeartbeat, Site]]:
    statement = select(AgentHeartbeat, Site).join(Site, AgentHeartbeat.site_id == Site.id).order_by(AgentHeartbeat.received_at.desc())
    if site_code:
        statement = statement.where(Site.code == site_code)
    statement = statement.limit(max(1, min(limit, 500)))
    result = await session.execute(statement)
    return [(heartbeat, site) for heartbeat, site in result.all()]


async def latest_agent_heartbeats(session: AsyncSession) -> list[tuple[AgentHeartbeat, Site]]:
    # Deduplicate in SQL across (site_id, agent_name) using window function
    row_num = func.row_number().over(
        partition_by=(AgentHeartbeat.site_id, AgentHeartbeat.agent_name),
        order_by=AgentHeartbeat.received_at.desc(),
    ).label("rn")
    subq = select(AgentHeartbeat.id, row_num).subquery()
    stmt = (
        select(AgentHeartbeat, Site)
        .join(Site, AgentHeartbeat.site_id == Site.id)
        .join(subq, AgentHeartbeat.id == subq.c.id)
        .where(subq.c.rn == 1)
        .order_by(AgentHeartbeat.received_at.desc())
    )
    result = await session.execute(stmt)
    return [(heartbeat, site) for heartbeat, site in result.all()]
