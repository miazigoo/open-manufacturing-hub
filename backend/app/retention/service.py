from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.core.enums import EventStatus
from app.events.models import IntegrationEvent


async def preview(session: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)
    expired_artifacts = (await session.execute(select(func.count()).select_from(Artifact).where(Artifact.expires_at.is_not(None), Artifact.expires_at <= now))).scalar_one()
    expired_events = (await session.execute(select(func.count()).select_from(IntegrationEvent).where(IntegrationEvent.expires_at.is_not(None), IntegrationEvent.expires_at <= now, IntegrationEvent.pinned.is_(False)))).scalar_one()
    pinned_skipped = (await session.execute(select(func.count()).select_from(IntegrationEvent).where(IntegrationEvent.expires_at.is_not(None), IntegrationEvent.expires_at <= now, IntegrationEvent.pinned.is_(True)))).scalar_one()
    return {"expired_artifacts": expired_artifacts, "expired_events": expired_events, "pinned_skipped": pinned_skipped}


async def cleanup_expired(session: AsyncSession) -> dict:
    stats = await preview(session)
    now = datetime.now(timezone.utc)
    artifacts = (await session.execute(select(Artifact).where(Artifact.expires_at.is_not(None), Artifact.expires_at <= now))).scalars().all()
    for artifact in artifacts:
        await session.delete(artifact)
    events = (await session.execute(select(IntegrationEvent).where(IntegrationEvent.expires_at.is_not(None), IntegrationEvent.expires_at <= now, IntegrationEvent.pinned.is_(False)))).scalars().all()
    for event in events:
        event.status = EventStatus.EXPIRED
    await session.flush()
    return stats
