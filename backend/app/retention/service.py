from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.core.config import get_settings
from app.core.enums import EventStatus
from app.events.models import IntegrationEvent
from app.health.models import HealthCheck


def _health_checks_cutoff(now: datetime) -> datetime:
    days = max(0.0, float(get_settings().health_checks_retention_days))
    return now - timedelta(days=days)


async def preview(session: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    expired_artifacts = (await session.execute(select(func.count()).select_from(Artifact).where(Artifact.expires_at.is_not(None), Artifact.expires_at <= now))).scalar_one()
    expired_events = (await session.execute(select(func.count()).select_from(IntegrationEvent).where(IntegrationEvent.expires_at.is_not(None), IntegrationEvent.expires_at <= now, IntegrationEvent.pinned.is_(False)))).scalar_one()
    pinned_skipped = (await session.execute(select(func.count()).select_from(IntegrationEvent).where(IntegrationEvent.expires_at.is_not(None), IntegrationEvent.expires_at <= now, IntegrationEvent.pinned.is_(True)))).scalar_one()
    old_health_checks = (await session.execute(select(func.count()).select_from(HealthCheck).where(HealthCheck.checked_at < _health_checks_cutoff(now)))).scalar_one()
    return {"expired_artifacts": expired_artifacts, "expired_events": expired_events, "pinned_skipped": pinned_skipped, "expired_health_checks": old_health_checks, "health_checks_retention_days": float(get_settings().health_checks_retention_days)}


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
    await session.flush()
    return stats
