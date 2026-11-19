from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient

from app.artifacts.models import Artifact
from app.core.config import get_settings
from app.core.database import get_session
from app.core.enums import ArtifactType, EnterpriseQueueStatus, EventStatus, HealthComponentType, HealthStatus, RunMode, RunStatus, StepStatus
from app.enterprise_runtime.models import DeadLetterQueueItem, IntegrationQueueMessage
from app.events.models import EventRun, EventStep, IntegrationEvent
from app.external_errors.models import ExternalErrorRecord
from app.health import readiness
from app.health.models import HealthCheck
from app.main import app
from scripts.restore_drill import detect_format, run_restore_drill, validate_target_db, verify_checksum


def test_restore_drill_target_db_safety():
    # 1. Exact match with production DB must fail with SAFETY VIOLATION
    with pytest.raises(ValueError, match="SAFETY VIOLATION"):
        validate_target_db("omh", "omh")

    with pytest.raises(ValueError, match="SAFETY VIOLATION"):
        validate_target_db("OMH", "omh")

    with pytest.raises(ValueError, match="SAFETY VIOLATION"):
        validate_target_db("  omh  ", "omh")

    # 2. System DBs must fail
    with pytest.raises(ValueError, match="system database"):
        validate_target_db("postgres", "omh")

    with pytest.raises(ValueError, match="system database"):
        validate_target_db("template1", "omh")

    # 3. Empty target DB must fail
    with pytest.raises(ValueError, match="cannot be empty"):
        validate_target_db("", "omh")

    # 4. Valid isolated target DB must succeed
    validate_target_db("omh_restore_drill_20261119_120000", "omh")
    validate_target_db("test_isolated_db", "prod_db")


def test_restore_drill_format_and_checksum(tmp_path: Path):
    # 1. Detect custom format from magic bytes
    dump_file = tmp_path / "test.dump"
    dump_file.write_bytes(b"PGDMP\x01\x02\x03fake_custom_dump")
    assert detect_format(dump_file) == "custom"

    # 2. Detect SQL format
    sql_file = tmp_path / "test.sql"
    sql_file.write_text("CREATE TABLE test (id int);", encoding="utf-8")
    assert detect_format(sql_file) == "sql"

    # 3. Verify valid checksum
    import hashlib
    actual_hash = hashlib.sha256(sql_file.read_bytes()).hexdigest()
    meta_file = tmp_path / "test.sql.meta.json"
    meta_file.write_text(json.dumps({"sha256": actual_hash}), encoding="utf-8")

    calc_hash, verified = verify_checksum(sql_file, meta_file)
    assert calc_hash == actual_hash
    assert verified is True

    # 4. Corrupted checksum must raise ValueError
    corrupt_meta = tmp_path / "corrupt.meta.json"
    corrupt_meta.write_text(json.dumps({"sha256": "wrong_hash_123"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Checksum verification failed"):
        verify_checksum(sql_file, corrupt_meta)


@pytest.mark.asyncio
async def test_run_restore_drill_safety_aborts(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist.dump"
    with pytest.raises(FileNotFoundError):
        await run_restore_drill(file_path=non_existent)

    existing_file = tmp_path / "valid.dump"
    existing_file.write_bytes(b"PGDMP\x01\x02\x03fake")
    # Must abort if target_db matches production_db
    with pytest.raises(ValueError, match="SAFETY VIOLATION"):
        await run_restore_drill(
            file_path=existing_file,
            target_db="omh",
            db_config={"host": "localhost", "port": 5432, "user": "omh", "password": "", "production_db": "omh"},
        )


@pytest.mark.asyncio
async def test_queue_and_dlq_endpoints_backwards_compatibility(session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        app.dependency_overrides[get_session] = lambda: session
        try:
            now = datetime.now(timezone.utc)
            # Create a queue message
            q_msg = IntegrationQueueMessage(
                event_id=uuid4(),
                business_object="order",
                operation="create",
                source_system="ERP",
                target_system="WMS",
                status=EnterpriseQueueStatus.WAITING,
                payload_json={"order_id": 12345, "items": ["sku-1"]},
                created_at=now,
            )
            session.add(q_msg)

            # Create a DLQ item
            dlq_item = DeadLetterQueueItem(
                event_id=uuid4(),
                business_object="invoice",
                operation="create",
                reason="TIMEOUT",
                last_error="Gateway timeout",
                payload_json={"invoice_id": 999},
                current_payload_json={"invoice_id": 999},
                created_at=now,
            )
            session.add(dlq_item)
            await session.commit()

            # 1. GET /api/queue with include_payload=false returns summaries without payload_json
            resp = await client.get("/api/queue?include_payload=false")
            assert resp.status_code == 200
            queue_list = resp.json()
            assert isinstance(queue_list, list)
            assert any(item["id"] == str(q_msg.id) and "payload_json" not in item for item in queue_list)

            # 1b. GET /api/queue by default returns the legacy full payload
            resp_full = await client.get("/api/queue")
            assert resp_full.status_code == 200
            queue_full = resp_full.json()
            assert any(item["id"] == str(q_msg.id) and item.get("payload_json") == {"order_id": 12345, "items": ["sku-1"]} for item in queue_full)

            # 2. GET /api/queue/page must return paginated response with items and cursors
            resp_page = await client.get("/api/queue/page?limit=10")
            assert resp_page.status_code == 200
            page_data = resp_page.json()
            assert "items" in page_data
            assert "next_cursor" in page_data
            assert "has_more" in page_data
            assert any(item["id"] == str(q_msg.id) and "payload_json" not in item for item in page_data["items"])

            # 3. GET /api/dlq with include_payload=false returns summaries without payload_json
            resp_dlq = await client.get("/api/dlq?include_payload=false")
            assert resp_dlq.status_code == 200
            dlq_list = resp_dlq.json()
            assert isinstance(dlq_list, list)
            assert any(item["id"] == str(dlq_item.id) and "payload_json" not in item for item in dlq_list)

            # 3b. GET /api/dlq by default returns the legacy full payload
            resp_dlq_full = await client.get("/api/dlq")
            assert resp_dlq_full.status_code == 200
            dlq_full = resp_dlq_full.json()
            assert any(item["id"] == str(dlq_item.id) and item.get("payload_json") == {"invoice_id": 999} for item in dlq_full)

            # 4. GET /api/dlq/page must return paginated response with items and cursors
            resp_dlq_page = await client.get("/api/dlq/page?limit=10")
            assert resp_dlq_page.status_code == 200
            dlq_page_data = resp_dlq_page.json()
            assert "items" in dlq_page_data
            assert "next_cursor" in dlq_page_data
            assert "has_more" in dlq_page_data
            assert any(item["id"] == str(dlq_item.id) and "payload_json" not in item for item in dlq_page_data["items"])
        finally:
            app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_event_overview_pagination_and_deferred_artifacts(session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        app.dependency_overrides[get_session] = lambda: session
        try:
            now = datetime.now(timezone.utc)
            event = IntegrationEvent(
                event_type="test.pagination",
                source_system="SystemA",
                status=EventStatus.FAILED,
                created_at=now,
            )
            session.add(event)
            await session.flush()

            # Create 3 runs for this event
            for r in range(1, 4):
                run = EventRun(
                    event_id=event.id,
                    run_number=r,
                    mode=RunMode.NORMAL if r == 1 else RunMode.REPLAY,
                    status=RunStatus.FAILED if r < 3 else RunStatus.SUCCESS,
                    created_at=now + timedelta(seconds=r),
                )
                session.add(run)
                await session.flush()

                step = EventStep(
                    run_id=run.id,
                    step_name="process",
                    step_order=1,
                    status=StepStatus.SUCCESS,
                )
                session.add(step)
                await session.flush()

                art = Artifact(
                    event_id=event.id,
                    run_id=run.id,
                    step_id=step.id,
                    artifact_type=ArtifactType.MAPPED_PAYLOAD.value,
                    name=f"artifact_run_{r}.json",
                    content_json={"run": r, "large_data": "x" * 100},
                    content_hash=f"hash_{r}",
                    size_bytes=100,
                    created_at=now + timedelta(seconds=r),
                )
                session.add(art)

                if r == 3:
                    ext_err = ExternalErrorRecord(
                        event_id=event.id,
                        run_id=run.id,
                        step_id=step.id,
                        normalized_code="ERR_HTTP_500",
                        normalized_message="Internal Server Error from upstream",
                        human_title="1C Server Error",
                        human_summary="1C OData service returned 500",
                        hint="Check 1C event log",
                    )
                    session.add(ext_err)

            await session.commit()

            # 1. Fetch overview with limit=2 -> should return 2 runs and has_more_runs=True
            resp = await client.get(f"/api/events/{event.id}/overview?limit=2&offset=0")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["runs"]) == 2
            assert data["has_more_runs"] is True
            # Newest run first (DESC)
            assert data["runs"][0]["run_number"] == 3
            assert data["runs"][1]["run_number"] == 2

            # Verify external error was attached to run 3 step
            run3_step = data["runs"][0]["steps"][0]
            assert run3_step["human_title"] == "1C Server Error"
            assert run3_step["hint"] == "Check 1C event log"

            # Artifacts in overview must NOT contain content_json (lazy-loaded / deferred)
            for r in data["runs"]:
                for art in r["artifacts"]:
                    assert art.get("content_json") is None

            brief = (await client.get(f"/api/events/{event.id}/overview?brief=true&limit=2")).json()
            assert all(not row["steps"] and not row["artifacts"] for row in brief["runs"])
            earlier = (await client.get(f"/api/events/{event.id}/overview", params={
                "brief": True, "before_run": brief["next_runs_cursor"],
            })).json()
            assert [row["run_number"] for row in earlier["runs"]] == [1]
            detail = await client.get(f"/api/events/{event.id}/runs/{earlier['runs'][0]['id']}/metadata")
            assert detail.json()["steps"][0]["artifacts"][0]["name"] == "artifact_run_1.json"

            # 2. Fetch next page with offset=2
            resp2 = await client.get(f"/api/events/{event.id}/overview?limit=2&offset=2")
            assert resp2.status_code == 200
            data2 = resp2.json()
            assert len(data2["runs"]) == 1
            assert data2["runs"][0]["run_number"] == 1
            assert data2["has_more_runs"] is False
        finally:
            app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_worker_heartbeat_age_threshold(session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        app.dependency_overrides[get_session] = lambda: session
        settings = get_settings()
        orig_require = settings.require_worker_heartbeat
        try:
            settings.require_worker_heartbeat = True
            now = datetime.now(timezone.utc)

            # 1. Heartbeat age 30s <= 180s -> ready 200
            fresh_hb = HealthCheck(
                component_type=HealthComponentType.AGENT,
                component_name="queue-worker",
                status=HealthStatus.OK,
                checked_at=now - timedelta(seconds=30),
            )
            session.add(fresh_hb)
            await session.commit()

            # Test worker_heartbeat_check helper directly
            hb_check = await readiness.worker_heartbeat_check(session)
            assert hb_check["status"] == "ok"
            assert "last heartbeat" in hb_check["message"]

            resp = await client.get("/api/health/ready")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] in ("ok", "warning")

            fresh_hb.status = HealthStatus.WARNING
            await session.commit()
            assert (await client.get("/api/health/ready")).status_code == 503
            fresh_hb.status = HealthStatus.OK

            # 2. Heartbeat age 200s > 180s -> error 503
            fresh_hb.checked_at = now - timedelta(seconds=200)
            await session.commit()

            # Test worker_heartbeat_check helper directly
            stale_check = await readiness.worker_heartbeat_check(session)
            assert stale_check["status"] == "error"
            assert "last heartbeat" in stale_check["message"]

            resp_stale = await client.get("/api/health/ready")
            assert resp_stale.status_code == 503
            data_stale = resp_stale.json()
            assert data_stale["status"] == "error"
            worker_check = next((c for c in data_stale["checks"] if c["name"] == "worker_heartbeat"), None)
            assert worker_check is not None
            assert worker_check["status"] == "error"
        finally:
            settings.require_worker_heartbeat = orig_require
            app.dependency_overrides.pop(get_session, None)


@pytest.mark.asyncio
async def test_queue_cursor_keeps_original_filter_and_order(client, session):
    session.add_all([
        IntegrationQueueMessage(business_object="order", operation="ship", priority=5)
        for _ in range(3)
    ])
    await session.commit()
    path = "/api/queue/page"
    first = (await client.get(path, params={"limit": 1, "operation": "ship"})).json()
    cursor = first["next_cursor"]
    second = await client.get(path, params={"limit": 1, "operation": "ship", "cursor": cursor})
    assert second.status_code == 200
    assert second.json()["items"][0]["id"] != first["items"][0]["id"]
    for changed in ({"operation": "receive"}, {"operation": "ship", "sort": "attempts"}):
        assert (await client.get(path, params={**changed, "cursor": cursor})).status_code == 422
