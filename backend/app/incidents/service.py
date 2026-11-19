import logging
import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import IncidentSeverity, IncidentStatus, NotificationTriggerType
from app.core.errors import NotFoundError
from app.events.models import EventRun, EventStep, IntegrationEvent
from app.incidents.models import Incident, IncidentEvent
from app.incidents.repository import get_by_fingerprint, get_incident

_UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
_NUMBER_RE = re.compile(r"\b\d+\b")
logger = logging.getLogger(__name__)


def normalize_error_message(message: str) -> str:
    normalized = _UUID_RE.sub("{uuid}", message.lower().strip())
    return _NUMBER_RE.sub("{number}", normalized)


def fingerprint(target_system: str | None, failed_step: str, error_code: str, message: str) -> str:
    return "|".join([target_system or "", failed_step, error_code, normalize_error_message(message)])


async def record_failure(session: AsyncSession, event: IntegrationEvent, run: EventRun, step: EventStep) -> Incident:
    error_code = step.error_code or "UNKNOWN"
    error_message = step.error_message or "Unknown error"
    normalized = normalize_error_message(error_message)
    fp = fingerprint(event.target_system, step.step_name, error_code, error_message)
    incident = await get_by_fingerprint(session, fp)
    created = False
    now = datetime.now(timezone.utc)
    if incident is None:
        incident = Incident(
            fingerprint=fp,
            title=f"{error_code} at {step.step_name}",
            status=IncidentStatus.OPEN,
            severity=IncidentSeverity.ERROR,
            source_system=event.source_system,
            target_system=event.target_system,
            failed_step=step.step_name,
            error_code=error_code,
            normalized_error_message=normalized,
            affected_events_count=0,
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(incident)
        await session.flush()
        created = True
    else:
        incident.last_seen_at = now

    existing_link = (
        await session.execute(
            select(IncidentEvent).where(
                IncidentEvent.incident_id == incident.id,
                IncidentEvent.event_id == event.id,
            )
        )
    ).scalar_one_or_none()
    if existing_link is None:
        link = IncidentEvent(incident_id=incident.id, event_id=event.id, run_id=run.id, step_id=step.id)
        session.add(link)
        incident.affected_events_count += 1
    await session.flush()

    from app.notifications.service import trigger_notifications

    await trigger_notifications(
        session,
        NotificationTriggerType.INCIDENT_CREATED if created else NotificationTriggerType.INCIDENT_UPDATED,
        incident_payload(incident),
    )
    return incident


def incident_payload(incident: Incident) -> dict:
    return {
        "incident_id": str(incident.id),
        "status": incident.status.value if hasattr(incident.status, "value") else incident.status,
        "severity": incident.severity.value if hasattr(incident.severity, "value") else incident.severity,
        "target_system": incident.target_system,
        "failed_step": incident.failed_step,
        "error_code": incident.error_code,
        "affected_events_count": incident.affected_events_count,
        "timeline_url": f"/api/incidents/{incident.id}",
    }


async def set_status(session: AsyncSession, incident_id: UUID, status: IncidentStatus) -> Incident:
    incident = await get_incident(session, incident_id)
    if incident is None:
        raise NotFoundError("Incident not found")
    incident.status = status
    now = datetime.now(timezone.utc)
    if status == IncidentStatus.ACKNOWLEDGED:
        incident.acknowledged_at = now
    if status == IncidentStatus.RESOLVED:
        incident.resolved_at = now
    await session.flush()
    return incident


async def safe_record_failure(session: AsyncSession, event: IntegrationEvent, run: EventRun, step: EventStep) -> Incident | None:
    try:
        return await record_failure(session, event, run, step)
    except Exception:
        logger.exception("Failed to record incident for event %s", event.id)
        return None


async def attach_external_error_samples(session: AsyncSession, incident: Incident) -> Incident:
    from app.external_errors.service import list_for_incident

    setattr(incident, "sample_external_errors", await list_for_incident(session, incident.id, limit=5))
    return incident


async def attach_external_error_samples_many(session: AsyncSession, incidents: list[Incident]) -> list[Incident]:
    if not incidents:
        return []
    incident_ids = [incident.id for incident in incidents]
    from app.external_errors.models import ExternalErrorRecord

    # Efficient batch query using window function to fetch up to 5 samples per incident
    row_num = func.row_number().over(
        partition_by=ExternalErrorRecord.incident_id,
        order_by=ExternalErrorRecord.created_at.desc(),
    ).label("rn")
    stmt = (
        select(ExternalErrorRecord, row_num)
        .where(ExternalErrorRecord.incident_id.in_(incident_ids))
        .subquery()
    )
    samples_stmt = select(ExternalErrorRecord).join(stmt, ExternalErrorRecord.id == stmt.c.id).where(stmt.c.rn <= 5)
    samples_res = await session.execute(samples_stmt)
    samples_by_incident: dict[UUID, list[ExternalErrorRecord]] = {}
    for sample in samples_res.scalars().all():
        if sample.incident_id:
            samples_by_incident.setdefault(sample.incident_id, []).append(sample)

    for incident in incidents:
        setattr(incident, "sample_external_errors", samples_by_incident.get(incident.id, []))
    return incidents
