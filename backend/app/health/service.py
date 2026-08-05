from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload

from app.core.enums import HealthComponentType, HealthStatus
from app.events.models import IntegrationEvent
from app.health.models import AgentHeartbeat, HealthCheck, Site
from app.health.repository import get_site_by_code, get_site_by_name, latest_agent_heartbeats, latest_checks, list_agent_heartbeats
from app.health.schemas import AgentHeartbeatCreate, AgentHeartbeatHistoryItem, AgentHeartbeatSummary, HealthCheckCreate

DEFAULT_AGENT_STALE_AFTER_SECONDS = 180


async def get_or_create_site(session: AsyncSession, name: str, code: str, description: str | None = None) -> Site:
    site = await get_site_by_code(session, code)
    if site is None:
        site = await get_site_by_name(session, name)
    if site is None:
        site = Site(name=name, code=code, description=description)
        session.add(site)
        await session.flush()
    return site


async def create_check(session: AsyncSession, request: HealthCheckCreate) -> HealthCheck:
    site = await get_site_by_code(session, request.site_code) if request.site_code else None
    check = HealthCheck(
        component_type=request.component_type,
        component_name=request.component_name,
        site_id=site.id if site else None,
        status=request.status,
        details_json=request.details_json,
        checked_at=datetime.now(timezone.utc),
    )
    session.add(check)
    await session.flush()
    return check


async def record_heartbeat(session: AsyncSession, request: AgentHeartbeatCreate) -> AgentHeartbeat:
    site = await get_or_create_site(session, request.site_name, request.site_code)
    heartbeat = AgentHeartbeat(
        site_id=site.id,
        agent_name=request.agent_name,
        internet_ok=request.internet_ok,
        can_reach_hub=request.can_reach_hub,
        can_reach_wms=request.can_reach_wms,
        can_reach_erp=request.can_reach_erp,
        local_ip=request.local_ip,
        details_json=request.details_json,
    )
    session.add(heartbeat)
    await session.flush()
    for name, ok in [("internet", request.internet_ok), ("hub", request.can_reach_hub), ("wms", request.can_reach_wms), ("erp", request.can_reach_erp)]:
        if ok is not None:
            session.add(
                HealthCheck(
                    component_type=HealthComponentType.SITE,
                    component_name=name,
                    site_id=site.id,
                    status=HealthStatus.OK if ok else HealthStatus.DOWN,
                    checked_at=datetime.now(timezone.utc),
                )
            )
    await session.flush()
    return heartbeat


def _signal_status(value: bool | None) -> HealthStatus:
    if value is True:
        return HealthStatus.OK
    if value is False:
        return HealthStatus.DOWN
    return HealthStatus.UNKNOWN


def _heartbeat_age_seconds(received_at: datetime, now: datetime) -> int:
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)
    return max(0, int((now - received_at).total_seconds()))


def heartbeat_summary(heartbeat: AgentHeartbeat, site: Site, stale_after_seconds: int = DEFAULT_AGENT_STALE_AFTER_SECONDS, now: datetime | None = None) -> AgentHeartbeatSummary:
    now = now or datetime.now(timezone.utc)
    age_seconds = _heartbeat_age_seconds(heartbeat.received_at, now)
    signals = [
        heartbeat.internet_ok,
        heartbeat.can_reach_hub,
        heartbeat.can_reach_wms,
        heartbeat.can_reach_erp,
    ]
    if age_seconds > stale_after_seconds:
        status = HealthStatus.DOWN
    elif any(value is False for value in signals):
        status = HealthStatus.WARNING
    elif any(value is True for value in signals):
        status = HealthStatus.OK
    else:
        status = HealthStatus.UNKNOWN
    return AgentHeartbeatSummary(
        id=heartbeat.id,
        site_id=site.id,
        site_name=site.name,
        site_code=site.code,
        agent_name=heartbeat.agent_name,
        status=status,
        heartbeat_age_seconds=age_seconds,
        stale_after_seconds=stale_after_seconds,
        internet=_signal_status(heartbeat.internet_ok),
        hub=_signal_status(heartbeat.can_reach_hub),
        wms=_signal_status(heartbeat.can_reach_wms),
        erp=_signal_status(heartbeat.can_reach_erp),
        local_ip=heartbeat.local_ip,
        details_json=heartbeat.details_json,
        received_at=heartbeat.received_at,
    )


async def agent_summaries(session: AsyncSession, stale_after_seconds: int = DEFAULT_AGENT_STALE_AFTER_SECONDS) -> list[AgentHeartbeatSummary]:
    now = datetime.now(timezone.utc)
    rows = await latest_agent_heartbeats(session)
    return [heartbeat_summary(heartbeat, site, stale_after_seconds, now) for heartbeat, site in rows]


async def agent_history(session: AsyncSession, limit: int = 100, site_code: str | None = None) -> list[AgentHeartbeatHistoryItem]:
    rows = await list_agent_heartbeats(session, limit=limit, site_code=site_code)
    return [
        AgentHeartbeatHistoryItem(
            id=heartbeat.id,
            site_id=heartbeat.site_id,
            site_name=site.name,
            site_code=site.code,
            agent_name=heartbeat.agent_name,
            internet_ok=heartbeat.internet_ok,
            can_reach_hub=heartbeat.can_reach_hub,
            can_reach_wms=heartbeat.can_reach_wms,
            can_reach_erp=heartbeat.can_reach_erp,
            local_ip=heartbeat.local_ip,
            details_json=heartbeat.details_json,
            received_at=heartbeat.received_at,
        )
        for heartbeat, site in rows
    ]


async def dashboard(session: AsyncSession) -> dict:
    result = await session.execute(select(Site).options(lazyload(Site.checks)))
    sites = list(result.scalars().all())
    checks = await latest_checks(session)
    latest_event_at = (await session.execute(select(func.max(IntegrationEvent.created_at)))).scalar_one_or_none()
    if latest_event_at is not None and latest_event_at.tzinfo is None:
        latest_event_at = latest_event_at.replace(tzinfo=timezone.utc)
    last_event_minutes_ago = None
    if latest_event_at is not None:
        last_event_minutes_ago = max(0, int((datetime.now(timezone.utc) - latest_event_at).total_seconds() / 60))

    site_rows = []
    agent_rows = await agent_summaries(session)
    agents_by_site = {}
    for agent in agent_rows:
        agents_by_site.setdefault(str(agent.site_id), []).append(agent)
    for site in sites:
        scoped = [c for c in checks if c.site_id == site.id]
        by_name = {c.component_name: c.status.value if hasattr(c.status, "value") else c.status for c in scoped}
        queue_check = next((c for c in scoped if c.component_name == "queue"), None)
        queue_size = 0
        if queue_check and isinstance(queue_check.details_json, dict):
            queue_size = int(queue_check.details_json.get("queue_size") or 0)
        statuses = list(by_name.values())
        status = "down" if "down" in statuses else "warning" if "warning" in statuses else "ok" if statuses else "unknown"
        site_agents = agents_by_site.get(str(site.id), [])
        if site_agents and any(agent.status == HealthStatus.DOWN for agent in site_agents):
            status = "down"
        elif site_agents and status != "down" and any(agent.status == HealthStatus.WARNING for agent in site_agents):
            status = "warning"
        latest_agent = max(site_agents, key=lambda agent: agent.received_at, default=None)
        site_rows.append(
            {
                "name": site.name,
                "code": site.code,
                "status": status,
                "internet": by_name.get("internet", "unknown"),
                "hub": by_name.get("hub", "unknown"),
                "wms": by_name.get("wms", "unknown"),
                "erp": by_name.get("erp", "unknown"),
                "queue_size": queue_size,
                "last_event_minutes_ago": last_event_minutes_ago,
                "agent_name": latest_agent.agent_name if latest_agent else None,
                "agent_status": latest_agent.status.value if latest_agent else "unknown",
                "last_heartbeat_at": latest_agent.received_at if latest_agent else None,
                "heartbeat_age_seconds": latest_agent.heartbeat_age_seconds if latest_agent else None,
            }
        )
    components = [
        {
            "name": c.component_name,
            "type": c.component_type.value if hasattr(c.component_type, "value") else c.component_type,
            "status": c.status.value if hasattr(c.status, "value") else c.status,
        }
        for c in checks
        if c.site_id is None
    ]
    return {"sites": site_rows, "components": components, "agents": [agent.model_dump(mode="json") for agent in agent_rows]}
