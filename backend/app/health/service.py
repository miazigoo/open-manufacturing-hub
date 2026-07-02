from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import HealthComponentType, HealthStatus
from app.events.models import IntegrationEvent
from app.health.models import AgentHeartbeat, HealthCheck, Site
from app.health.repository import get_site_by_code, latest_checks
from app.health.schemas import AgentHeartbeatCreate, HealthCheckCreate


async def get_or_create_site(session: AsyncSession, name: str, code: str, description: str | None = None) -> Site:
    site = await get_site_by_code(session, code)
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


async def dashboard(session: AsyncSession) -> dict:
    result = await session.execute(select(Site))
    sites = list(result.scalars().all())
    checks = await latest_checks(session)
    latest_event_at = (await session.execute(select(func.max(IntegrationEvent.created_at)))).scalar_one_or_none()
    if latest_event_at is not None and latest_event_at.tzinfo is None:
        latest_event_at = latest_event_at.replace(tzinfo=timezone.utc)
    last_event_minutes_ago = None
    if latest_event_at is not None:
        last_event_minutes_ago = max(0, int((datetime.now(timezone.utc) - latest_event_at).total_seconds() / 60))

    site_rows = []
    for site in sites:
        scoped = [c for c in checks if c.site_id == site.id]
        by_name = {c.component_name: c.status.value if hasattr(c.status, "value") else c.status for c in scoped}
        queue_check = next((c for c in scoped if c.component_name == "queue"), None)
        queue_size = 0
        if queue_check and isinstance(queue_check.details_json, dict):
            queue_size = int(queue_check.details_json.get("queue_size") or 0)
        statuses = list(by_name.values())
        status = "down" if "down" in statuses else "warning" if "warning" in statuses else "ok" if statuses else "unknown"
        site_rows.append(
            {
                "name": site.name,
                "status": status,
                "internet": by_name.get("internet", "unknown"),
                "wms": by_name.get("wms", "unknown"),
                "erp": by_name.get("erp", "unknown"),
                "queue_size": queue_size,
                "last_event_minutes_ago": last_event_minutes_ago,
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
    return {"sites": site_rows, "components": components}
