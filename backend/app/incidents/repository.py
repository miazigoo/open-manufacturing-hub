from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.incidents.models import Incident, IncidentEvent


async def list_incidents(session: AsyncSession, limit: int = 100) -> list[Incident]:
    result = await session.execute(select(Incident).order_by(Incident.last_seen_at.desc()).limit(limit))
    return list(result.scalars().all())


async def get_incident(session: AsyncSession, incident_id: UUID) -> Incident | None:
    return await session.get(Incident, incident_id)


async def get_by_fingerprint(session: AsyncSession, fingerprint: str) -> Incident | None:
    result = await session.execute(select(Incident).where(Incident.fingerprint == fingerprint))
    return result.scalar_one_or_none()


async def list_incident_events(session: AsyncSession, incident_id: UUID, limit: int = 100) -> list[IncidentEvent]:
    from app.events.models import IntegrationEvent
    stmt = (
        select(IncidentEvent, IntegrationEvent)
        .outerjoin(IntegrationEvent, IncidentEvent.event_id == IntegrationEvent.id)
        .where(IncidentEvent.incident_id == incident_id)
        .order_by(IncidentEvent.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    items = []
    for link, event in result.all():
        if event:
            link.event_type = event.event_type
            link.event_status = event.status.value if hasattr(event.status, "value") else str(event.status)
            link.entity_type = event.entity_type
            link.entity_id = event.entity_id
        items.append(link)
    return items
