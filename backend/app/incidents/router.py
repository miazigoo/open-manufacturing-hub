from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.enums import IncidentStatus
from app.core.errors import NotFoundError
from app.incidents import repository, service
from app.incidents.schemas import IncidentEventRead, IncidentRead

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentRead])
async def list_incidents(session: AsyncSession = Depends(get_session)):
    incidents = await repository.list_incidents(session)
    return await service.attach_external_error_samples_many(session, incidents)


@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident(incident_id: UUID, session: AsyncSession = Depends(get_session)):
    incident = await repository.get_incident(session, incident_id)
    if incident is None:
        raise NotFoundError("Incident not found")
    return await service.attach_external_error_samples(session, incident)


@router.get("/{incident_id}/events", response_model=list[IncidentEventRead])
async def get_incident_events(incident_id: UUID, session: AsyncSession = Depends(get_session)):
    return await repository.list_incident_events(session, incident_id)


@router.post("/{incident_id}/acknowledge", response_model=IncidentRead)
async def acknowledge(incident_id: UUID, session: AsyncSession = Depends(get_session)):
    incident = await service.set_status(session, incident_id, IncidentStatus.ACKNOWLEDGED)
    await session.commit()
    return incident


@router.post("/{incident_id}/resolve", response_model=IncidentRead)
async def resolve(incident_id: UUID, session: AsyncSession = Depends(get_session)):
    incident = await service.set_status(session, incident_id, IncidentStatus.RESOLVED)
    await session.commit()
    return incident


@router.post("/{incident_id}/ignore", response_model=IncidentRead)
async def ignore(incident_id: UUID, session: AsyncSession = Depends(get_session)):
    incident = await service.set_status(session, incident_id, IncidentStatus.IGNORED)
    await session.commit()
    return incident
