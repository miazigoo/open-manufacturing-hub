from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient

from app.artifacts.models import Artifact
from app.core.database import get_session
from app.core.enums import EnterpriseQueueStatus, EventStatus, RunMode, RunStatus
from app.enterprise_runtime.models import IntegrationQueueMessage
from app.enterprise_runtime.service import eligible_queue_item, schedule_retry_or_dlq
from app.events.models import EventRun, IntegrationEvent
from app.health import readiness
from app.main import app
from app.production.backups import create_db_backup
from app.production.models import BackupStatus
from app.retention.service import cleanup_expired, preview


@pytest.mark.asyncio
async def test_retention_preserves_pinned_event_and_artifacts(session):
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=60)

    # 1. Pinned event + artifact (must be preserved)
    pinned_ev = IntegrationEvent(
        event_type="order.created",
        source_system="1C",
        status=EventStatus.SUCCESS,
        pinned=True,
        created_at=old_time,
    )
    session.add(pinned_ev)
    await session.flush()

    pinned_run = EventRun(
        event_id=pinned_ev.id,
        run_number=1,
        mode=RunMode.NORMAL,
        status=RunStatus.SUCCESS,
        created_at=old_time,
    )
    session.add(pinned_run)
    await session.flush()

    pinned_art = Artifact(
        event_id=pinned_ev.id,
        run_id=pinned_run.id,
        artifact_type="payload",
        name="pinned_payload.json",
        content_json={"key": "pinned"},
        content_hash="hash1",
        size_bytes=10,
        created_at=old_time,
    )
    session.add(pinned_art)

    # 2. Unpinned event + artifact (should be cleaned up)
    unpinned_ev = IntegrationEvent(
        event_type="order.created",
        source_system="1C",
        status=EventStatus.SUCCESS,
        pinned=False,
        created_at=old_time,
    )
    session.add(unpinned_ev)
    await session.flush()

    unpinned_run = EventRun(
        event_id=unpinned_ev.id,
        run_number=1,
        mode=RunMode.NORMAL,
        status=RunStatus.SUCCESS,
        created_at=old_time,
    )
    session.add(unpinned_run)
    await session.flush()

    unpinned_art = Artifact(
        event_id=unpinned_ev.id,
        run_id=unpinned_run.id,
        artifact_type="payload",
        name="unpinned_payload.json",
        content_json={"key": "unpinned"},
        content_hash="hash2",
        size_bytes=10,
        created_at=old_time,
    )
    session.add(unpinned_art)
    await session.commit()

    # Verify preview and cleanup
    stats = await preview(session)
    assert stats["aged_artifacts"] >= 1
    assert stats["aged_events"] >= 1

    await cleanup_expired(session)
    await session.commit()

    # Pinned event and its artifact MUST still exist
    assert await session.get(IntegrationEvent, pinned_ev.id) is not None
    assert await session.get(Artifact, pinned_art.id) is not None

    # Unpinned event and artifact MUST be deleted
    assert await session.get(IntegrationEvent, unpinned_ev.id) is None
    assert await session.get(Artifact, unpinned_art.id) is None


@pytest.mark.asyncio
async def test_queue_stale_processing_recovery_and_claim(session):
    now = datetime.now(timezone.utc)
    stale_time = now - timedelta(seconds=600)

    # Queue message stuck in PROCESSING from crashed worker
    stuck_msg = IntegrationQueueMessage(
        business_object="Order",
        operation="sync",
        status=EnterpriseQueueStatus.PROCESSING,
        worker="crashed-worker",
        locked_by="crashed-worker",
        locked_at=stale_time,
        locked_until=stale_time + timedelta(seconds=60), # Expired!
        attempts=1,
    )
    session.add(stuck_msg)
    await session.commit()

    # Calling eligible_queue_item with new worker recovers and claims the message
    claimed = await eligible_queue_item(session, worker="healthy-worker")
    assert claimed is not None
    assert claimed.id == stuck_msg.id
    assert claimed.status == EnterpriseQueueStatus.PROCESSING
    assert claimed.worker == "healthy-worker"
    assert claimed.locked_by == "healthy-worker"
    assert claimed.locked_until > now


@pytest.mark.asyncio
async def test_infinite_retry_storm_prevention(session):
    item = IntegrationQueueMessage(
        business_object="LaserMarking",
        operation="laser_file",
        status=EnterpriseQueueStatus.PROCESSING,
        attempts=3,
        max_attempts=10,
        payload_json={"retry_policy": "infinite"},
    )
    session.add(item)
    await session.commit()

    # Attempt 3 should schedule retry WITHOUT moving to DLQ and WITHOUT spamming notifications
    await schedule_retry_or_dlq(session, item, "DEVICE_TIMEOUT", "Laser head offline")
    assert item.status == EnterpriseQueueStatus.RETRY_WAITING
    assert item.last_error_code == "DEVICE_TIMEOUT"


@pytest.mark.asyncio
async def test_readiness_returns_503_on_error(session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        app.dependency_overrides[get_session] = lambda: session
        try:
            # 1. Normal state should be ready (200)
            resp = await client.get("/api/health/ready")
            assert resp.status_code == 200

            # 2. Simulate critical readiness failure
            original_ready = readiness.ready
            async def failing_ready(_):
                return {
                    "status": "error",
                    "checks": [{"name": "database", "status": "error", "message": "connection refused"}],
                }
            readiness.ready = failing_ready
            try:
                fail_resp = await client.get("/api/health/ready")
                assert fail_resp.status_code == 503
                data = fail_resp.json()
                assert data["status"] == "error"
            finally:
                readiness.ready = original_ready
        finally:
            app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_db_backup_creates_verifiable_dump_and_checksum(session):
    record = await create_db_backup(session, created_by="test-suite")
    await session.commit()

    assert record.status == BackupStatus.SUCCESS
    assert record.file_path is not None
    assert record.size_bytes is not None and record.size_bytes > 0
    assert "format" in record.metadata_json
    assert "sha256" in record.metadata_json

    # Verify sha256 checksum against actual file on disk
    with open(record.file_path, "rb") as f:
        computed_sha256 = hashlib.sha256(f.read()).hexdigest()
    assert record.metadata_json["sha256"] == computed_sha256
