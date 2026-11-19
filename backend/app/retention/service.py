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
    pinned_event_ids = select(IntegrationEvent.id).where(IntegrationEvent.pinned.is_(True)).scalar_subquery()

    expired_artifacts = (
        await session.execute(
            select(func.count())
            .select_from(Artifact)
            .where(
                Artifact.expires_at.is_not(None),
                Artifact.expires_at <= now,
                Artifact.event_id.not_in(pinned_event_ids),
            )
        )
    ).scalar_one()

    expired_events = (
        await session.execute(
            select(func.count())
            .select_from(IntegrationEvent)
            .where(
                IntegrationEvent.expires_at.is_not(None),
                IntegrationEvent.expires_at <= now,
                IntegrationEvent.pinned.is_(False),
            )
        )
    ).scalar_one()

    pinned_skipped = (
        await session.execute(
            select(func.count())
            .select_from(IntegrationEvent)
            .where(
                IntegrationEvent.expires_at.is_not(None),
                IntegrationEvent.expires_at <= now,
                IntegrationEvent.pinned.is_(True),
            )
        )
    ).scalar_one()

    old_health_checks = (
        await session.execute(
            select(func.count())
            .select_from(HealthCheck)
            .where(HealthCheck.checked_at < _health_checks_cutoff(now))
        )
    ).scalar_one()

    aged_artifacts = (
        await session.execute(
            select(func.count())
            .select_from(Artifact)
            .where(
                Artifact.created_at < _artifacts_cutoff(now),
                Artifact.event_id.not_in(pinned_event_ids),
            )
        )
    ).scalar_one()

    aged_events = (
        await session.execute(
            select(func.count())
            .select_from(IntegrationEvent)
            .where(
                IntegrationEvent.created_at < _events_cutoff(now),
                IntegrationEvent.pinned.is_(False),
            )
        )
    ).scalar_one()

    aged_inbox = 0
    days_templates = (
        await session.execute(
            select(InboxTemplate.id, InboxTemplate.storage_days).where(InboxTemplate.storage_mode == "days")
        )
    ).all()
    for template_id, storage_days in days_templates:
        cutoff = (now - timedelta(days=max(1, int(storage_days)))).replace(tzinfo=None)
        aged_inbox += (
            await session.execute(
                select(func.count())
                .select_from(InboxRecord)
                .where(InboxRecord.template_id == template_id, InboxRecord.created_at < cutoff)
            )
        ).scalar_one()

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
    pinned_event_ids = select(IntegrationEvent.id).where(IntegrationEvent.pinned.is_(True)).scalar_subquery()

    # 1. Expired artifacts (respecting pinned parent events)
    await session.execute(
        delete(Artifact).where(
            Artifact.expires_at.is_not(None),
            Artifact.expires_at <= now,
            Artifact.event_id.not_in(pinned_event_ids),
        )
    )

    # 2. Expired events
    events = (
        await session.execute(
            select(IntegrationEvent).where(
                IntegrationEvent.expires_at.is_not(None),
                IntegrationEvent.expires_at <= now,
                IntegrationEvent.pinned.is_(False),
            )
        )
    ).scalars().all()
    for event in events:
        event.status = EventStatus.EXPIRED

    # 3. Health checks
    await session.execute(delete(HealthCheck).where(HealthCheck.checked_at < _health_checks_cutoff(now)))

    # 4. Age-based inbox records cleanup
    days_templates = select(InboxTemplate.id).where(InboxTemplate.storage_mode == "days").scalar_subquery()
    for template_id in (
        await session.execute(
            select(InboxTemplate.id, InboxTemplate.storage_days).where(InboxTemplate.id.in_(days_templates))
        )
    ).all():
        cutoff = (now - timedelta(days=max(1, int(template_id[1])))).replace(tzinfo=None)
        await session.execute(
            delete(InboxRecord).where(InboxRecord.template_id == template_id[0], InboxRecord.created_at < cutoff)
        )

    # 5. Age-based artifact cleanup (preserving pinned event artifacts)
    await session.execute(
        delete(Artifact).where(
            Artifact.created_at < _artifacts_cutoff(now),
            Artifact.event_id.not_in(pinned_event_ids),
        )
    )

    # 6. Age-based event hierarchy cleanup (only unpinned events)
    old_event_ids = select(IntegrationEvent.id).where(
        IntegrationEvent.created_at < _events_cutoff(now),
        IntegrationEvent.pinned.is_(False),
    ).scalar_subquery()
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
