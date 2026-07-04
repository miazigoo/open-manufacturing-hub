from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.health.models import AgentHeartbeat, HealthCheck, Site


async def get_site_by_code(session: AsyncSession, code: str) -> Site | None:
    result = await session.execute(select(Site).where(Site.code == code))
    return result.scalar_one_or_none()


async def get_site_by_name(session: AsyncSession, name: str) -> Site | None:
    result = await session.execute(select(Site).where(Site.name == name))
    return result.scalar_one_or_none()


async def latest_checks(session: AsyncSession) -> list[HealthCheck]:
    result = await session.execute(select(HealthCheck).order_by(HealthCheck.checked_at.desc()))
    checks = list(result.scalars().all())
    seen: set[tuple[str, str, str | None]] = set()
    latest = []
    for check in checks:
        key = (check.component_type.value if hasattr(check.component_type, "value") else check.component_type, check.component_name, str(check.site_id) if check.site_id else None)
        if key not in seen:
            seen.add(key)
            latest.append(check)
    return latest


async def list_agent_heartbeats(session: AsyncSession, limit: int = 100, site_code: str | None = None) -> list[tuple[AgentHeartbeat, Site]]:
    statement = select(AgentHeartbeat, Site).join(Site, AgentHeartbeat.site_id == Site.id).order_by(AgentHeartbeat.received_at.desc())
    if site_code:
        statement = statement.where(Site.code == site_code)
    statement = statement.limit(max(1, min(limit, 500)))
    result = await session.execute(statement)
    return [(heartbeat, site) for heartbeat, site in result.all()]


async def latest_agent_heartbeats(session: AsyncSession) -> list[tuple[AgentHeartbeat, Site]]:
    rows = await list_agent_heartbeats(session, limit=500)
    seen: set[tuple[str, str]] = set()
    latest: list[tuple[AgentHeartbeat, Site]] = []
    for heartbeat, site in rows:
        key = (str(site.id), heartbeat.agent_name)
        if key in seen:
            continue
        seen.add(key)
        latest.append((heartbeat, site))
    return latest
