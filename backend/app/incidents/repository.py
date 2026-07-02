from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.incidents.models import Incident, IncidentEvent


async def list_incidents(session: AsyncSession) -> list[Incident]:
    result = await session.execute(select(Incident).order_by(Incident.last_seen_at.desc()))
    return list(result.scalars().all())


async def get_incident(session: AsyncSession, incident_id: UUID) -> Incident | None:
    return await session.get(Incident, incident_id)


async def get_by_fingerprint(session: AsyncSession, fingerprint: str) -> Incident | None:
    result = await session.execute(select(Incident).where(Incident.fingerprint == fingerprint))
    return result.scalar_one_or_none()


async def list_incident_events(session: AsyncSession, incident_id: UUID) -> list[IncidentEvent]:
    result = await session.execute(select(IncidentEvent).where(IncidentEvent.incident_id == incident_id))
    return list(result.scalars().all())
