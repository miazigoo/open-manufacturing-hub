from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.artifacts.models import Artifact
from app.core.database import async_session
from app.events.models import IntegrationEvent


async def test_retention_deletes_expired_artifacts_and_marks_events_expired(client, success_payload):
    event = (await client.post("/api/events", json=success_payload)).json()
    past = datetime.now(timezone.utc) - timedelta(days=1)
    async with async_session() as session:
        db_event = await session.get(IntegrationEvent, UUID(event["id"]))
        db_event.expires_at = past
        db_event.pinned = False
        artifact = (await session.execute(__import__("sqlalchemy").select(Artifact).limit(1))).scalar_one()
        artifact.expires_at = past
        await session.commit()

    preview = (await client.get("/api/retention/preview")).json()
    assert preview["expired_artifacts"] == 1
    assert preview["expired_events"] == 1

    cleanup = (await client.post("/api/retention/cleanup")).json()
    assert cleanup["expired_artifacts"] == 1
    assert (await client.get(f"/api/events/{event['id']}")).json()["status"] == "expired"


async def test_retention_skips_pinned_events(client, success_payload):
    event = (await client.post("/api/events", json=success_payload)).json()
    past = datetime.now(timezone.utc) - timedelta(days=1)
    async with async_session() as session:
        db_event = await session.get(IntegrationEvent, UUID(event["id"]))
        db_event.expires_at = past
        db_event.pinned = True
        await session.commit()

    preview = (await client.get("/api/retention/preview")).json()
    assert preview["expired_events"] == 0
    assert preview["pinned_skipped"] == 1


async def test_retention_deletes_old_health_checks(client, success_payload):
    from app.core.enums import HealthComponentType, HealthStatus
    from app.health.models import HealthCheck

    async with async_session() as session:
        old_check = HealthCheck(component_type=HealthComponentType.SITE, component_name="hub", status=HealthStatus.OK, checked_at=datetime.now(timezone.utc) - timedelta(days=30))
        fresh_check = HealthCheck(component_type=HealthComponentType.SITE, component_name="hub", status=HealthStatus.OK, checked_at=datetime.now(timezone.utc))
        session.add(old_check)
        session.add(fresh_check)
        await session.commit()

    preview = (await client.get("/api/retention/preview")).json()
    assert preview["expired_health_checks"] == 1
    assert preview["health_checks_retention_days"] == 7.0

    await client.post("/api/retention/cleanup")
    async with async_session() as session:
        remaining = (await session.execute(__import__("sqlalchemy").select(HealthCheck))).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].id == fresh_check.id
