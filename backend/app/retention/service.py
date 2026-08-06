from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.core.config import get_settings
from app.core.enums import EventStatus
from app.enterprise_runtime.models import IntegrationQueueMessage
from app.events.models import EventRun, EventStep, IntegrationEvent
from app.external_errors.models import ExternalErrorRecord
from app.health.models import HealthCheck
from app.data_inbox.models import InboxRecord, InboxTemplate


def _health_checks_cutoff(now: datetime) -> datetime:
    days = max(0.0, float(get_settings().health_checks_retention_days))
    return now - timedelta(days=days)


def _events_cutoff(now: datetime) -> datetime:
    days = max(0.0, float(get_settings().retention_events_days))
    return (now - timedelta(days=days)).replace(tzinfo=None)


def _artifacts_cutoff(now: datetime) -> datetime:
    days = max(0.0, float(get_settings().retention_artifacts_days))
    return (now - timedelta(days=days)).replace(tzinfo=None)


async def preview(session: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    expired_artifacts = (await session.execute(select(func.count()).select_from(Artifact).where(Artifact.expires_at.is_not(None), Artifact.expires_at <= now))).scalar_one()
    expired_events = (await session.execute(select(func.count()).select_from(IntegrationEvent).where(IntegrationEvent.expires_at.is_not(None), IntegrationEvent.expires_at <= now, IntegrationEvent.pinned.is_(False)))).scalar_one()
    pinned_skipped = (await session.execute(select(func.count()).select_from(IntegrationEvent).where(IntegrationEvent.expires_at.is_not(None), IntegrationEvent.expires_at <= now, IntegrationEvent.pinned.is_(True)))).scalar_one()
    old_health_checks = (await session.execute(select(func.count()).select_from(HealthCheck).where(HealthCheck.checked_at < _health_checks_cutoff(now)))).scalar_one()
    aged_artifacts = (await session.execute(select(func.count()).select_from(Artifact).where(Artifact.created_at < _artifacts_cutoff(now)))).scalar_one()
    aged_events = (await session.execute(select(func.count()).select_from(IntegrationEvent).where(IntegrationEvent.created_at < _events_cutoff(now), IntegrationEvent.pinned.is_(False)))).scalar_one()
    aged_inbox = 0
    days_templates = (await session.execute(select(InboxTemplate.id, InboxTemplate.storage_days).where(InboxTemplate.storage_mode == "days"))).all()
    for template_id, storage_days in days_templates:
        cutoff = (now - timedelta(days=max(1, int(storage_days)))).replace(tzinfo=None)
        aged_inbox += (await session.execute(select(func.count()).select_from(InboxRecord).where(InboxRecord.template_id == template_id, InboxRecord.created_at < cutoff))).scalar_one()
    return {
        "expired_artifacts": expired_artifacts,
        "expired_events": expired_events,
        "pinned_skipped": pinned_skipped,
        "expired_health_checks": old_health_checks,
        "health_checks_retention_days": float(get_settings().health_checks_retention_days),
        "aged_artifacts": aged_artifacts,
        "aged_events": aged_events,
        "retention_artifacts_days": float(get_settings().retention_artifacts_days),
        "retention_events_days": float(get_settings().retention_events_days),
        "aged_inbox_records": aged_inbox,
    }


async def cleanup_expired(session: AsyncSession) -> dict:
    stats = await preview(session)
    now = datetime.now(timezone.utc)
    artifacts = (await session.execute(select(Artifact).where(Artifact.expires_at.is_not(None), Artifact.expires_at <= now))).scalars().all()
    for artifact in artifacts:
        await session.delete(artifact)
    events = (await session.execute(select(IntegrationEvent).where(IntegrationEvent.expires_at.is_not(None), IntegrationEvent.expires_at <= now, IntegrationEvent.pinned.is_(False)))).scalars().all()
    for event in events:
        event.status = EventStatus.EXPIRED
    await session.execute(delete(HealthCheck).where(HealthCheck.checked_at < _health_checks_cutoff(now)))
    # Age-based inbox records cleanup: templates with storage_mode="days" keep
    # records only for storage_days; "forever" and "none" are never touched.
    days_templates = select(InboxTemplate.id).where(InboxTemplate.storage_mode == "days").scalar_subquery()
    for template_id in (await session.execute(select(InboxTemplate.id, InboxTemplate.storage_days).where(InboxTemplate.id.in_(days_templates)))).all():
        cutoff = (now - timedelta(days=max(1, int(template_id[1])))).replace(tzinfo=None)
        await session.execute(delete(InboxRecord).where(InboxRecord.template_id == template_id[0], InboxRecord.created_at < cutoff))
    # Age-based cleanup: heavy artifact payloads (CHZ pools in base64) and their
    # events must not accumulate forever. Pinned events are always preserved.
    await session.execute(delete(Artifact).where(Artifact.created_at < _artifacts_cutoff(now)))
    old_event_ids = select(IntegrationEvent.id).where(IntegrationEvent.created_at < _events_cutoff(now), IntegrationEvent.pinned.is_(False)).scalar_subquery()
    old_run_ids = select(EventRun.id).where(EventRun.event_id.in_(old_event_ids)).scalar_subquery()
    await session.execute(delete(EventStep).where(EventStep.run_id.in_(old_run_ids)))
    await session.execute(delete(Artifact).where(Artifact.event_id.in_(old_event_ids)))
    await session.execute(delete(Artifact).where(Artifact.run_id.in_(old_run_ids)))
    await session.execute(delete(ExternalErrorRecord).where(ExternalErrorRecord.event_id.in_(old_event_ids)))
    await session.execute(delete(IntegrationQueueMessage).where(IntegrationQueueMessage.event_id.in_(old_event_ids)))
    await session.execute(delete(EventRun).where(EventRun.event_id.in_(old_event_ids)))
    await session.execute(delete(IntegrationEvent).where(IntegrationEvent.id.in_(old_event_ids)))
    await session.flush()
    return stats
