import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from httpx import AsyncClient

from app.core.enums import EnterpriseQueueStatus, EventStatus
from app.enterprise_runtime.models import IntegrationQueueMessage, DeadLetterQueueItem
from app.enterprise_runtime.schemas import QueueMessageCreate
from app.events.models import IntegrationEvent, EventRun, EventStep
from app.artifacts.models import Artifact
from app.health.models import Site, AgentHeartbeat


@pytest.mark.asyncio
async def test_queue_sorting_distinct_priority_and_created(client: AsyncClient, session):
    # Create item A with high priority (10) but created earlier
    # Create item B with low priority (100) but created later
    # When sorting by priority, A should come before B
    # When sorting by created_at, B should come before A
    now = datetime.now(timezone.utc)
    item_a = IntegrationQueueMessage(
        business_object="ItemA",
        operation="sync",
        priority=10,
        status=EnterpriseQueueStatus.WAITING,
        created_at=now - timedelta(hours=2),
        payload_json={"name": "A", "huge": "x" * 1000},
    )
    item_b = IntegrationQueueMessage(
        business_object="ItemB",
        operation="sync",
        priority=100,
        status=EnterpriseQueueStatus.WAITING,
        created_at=now - timedelta(hours=1),
        payload_json={"name": "B", "huge": "y" * 1000},
    )
    session.add_all([item_a, item_b])
    await session.commit()

    # 1. Test sorting by priority
    res_prio = await client.get("/api/queue?sort=priority&include_payload=false")
    assert res_prio.status_code == 200
    data_prio = res_prio.json()
    assert len(data_prio) >= 2
    ids_prio = [d["id"] for d in data_prio]
    assert ids_prio.index(str(item_a.id)) < ids_prio.index(str(item_b.id))
    # Check that payload_json is excluded in summary
    assert "payload_json" not in data_prio[0]

    # 2. Test sorting by created_at
    res_created = await client.get("/api/queue?sort=created_at")
    assert res_created.status_code == 200
    data_created = res_created.json()
    ids_created = [d["id"] for d in data_created]
    assert ids_created.index(str(item_b.id)) < ids_created.index(str(item_a.id))

    # 3. Test single item get returns full payload
    res_single = await client.get(f"/api/queue/{item_a.id}")
    assert res_single.status_code == 200
    assert "payload_json" in res_single.json()
    assert res_single.json()["payload_json"]["name"] == "A"


@pytest.mark.asyncio
async def test_dlq_summary_excludes_payload(client: AsyncClient, session):
    dlq_item = DeadLetterQueueItem(
        business_object="DLQTest",
        operation="fail",
        reason="Exhausted",
        payload_json={"original": "secret_data"},
        current_payload_json={"current": "state"},
    )
    session.add(dlq_item)
    await session.commit()

    res = await client.get("/api/dlq?include_payload=false")
    assert res.status_code == 200
    items = res.json()
    target = next(i for i in items if i["id"] == str(dlq_item.id))
    assert "payload_json" not in target
    assert "current_payload_json" not in target
    assert target["business_object"] == "DLQTest"

    # Detail endpoint returns full payload
    res_item = await client.get(f"/api/dlq/{dlq_item.id}")
    assert res_item.status_code == 200
    assert res_item.json()["payload_json"]["original"] == "secret_data"


@pytest.mark.asyncio
async def test_event_overview_and_deferred_artifact_content(client: AsyncClient, session):
    event = IntegrationEvent(
        source_system="ERP",
        target_system="MES",
        event_type="order.created",
        status=EventStatus.SUCCESS,
    )
    session.add(event)
    await session.flush()

    run = EventRun(
        event_id=event.id,
        run_number=1,
        mode="normal",
        status="success",
    )
    session.add(run)
    await session.flush()

    step = EventStep(
        run_id=run.id,
        step_order=1,
        step_name="validate_order",
        status="success",
        step_config_json={},
    )
    session.add(step)
    await session.flush()

    artifact = Artifact(
        event_id=event.id,
        run_id=run.id,
        step_id=step.id,
        artifact_type="outgoing_request",
        name="payload.json",
        content_json={"massive_data": "Z" * 50000},
        content_hash="abc123hash",
        size_bytes=50000,
    )
    session.add(artifact)
    await session.commit()

    # GET overview
    res_ov = await client.get(f"/api/events/{event.id}/overview")
    assert res_ov.status_code == 200
    ov_data = res_ov.json()
    assert ov_data["event"]["event_type"] == "order.created"
    assert len(ov_data["runs"]) == 1
    run_0 = ov_data["runs"][0]
    assert len(run_0["steps"]) == 1
    step_0 = run_0["steps"][0]
    assert len(step_0["artifacts"]) == 1
    art_meta = step_0["artifacts"][0]
    assert art_meta["name"] == "payload.json"
    assert art_meta["size_bytes"] == 50000
    # Artifact summary in overview MUST NOT contain content_json
    assert "content_json" not in art_meta

    # Fetching artifact directly loads full body
    res_art = await client.get(f"/api/artifacts/{artifact.id}")
    assert res_art.status_code == 200
    assert res_art.json()["content_json"]["massive_data"] == "Z" * 50000


@pytest.mark.asyncio
async def test_dashboard_summary_interval_and_stats(client: AsyncClient, session):
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=2)

    # Event today - failed
    e_today_fail = IntegrationEvent(
        source_system="A", target_system="B", event_type="today.fail", status=EventStatus.FAILED, created_at=now
    )
    # Event yesterday - failed (should not count towards failed_today)
    e_yest_fail = IntegrationEvent(
        source_system="A", target_system="B", event_type="yest.fail", status=EventStatus.FAILED, created_at=yesterday
    )
    session.add_all([e_today_fail, e_yest_fail])
    await session.commit()

    res = await client.get("/api/events/dashboard-summary")
    assert res.status_code == 200
    d = res.json()
    assert d["timezone"] == "UTC"
    assert d["failed_today"] >= 1
    # Both events are failed, so latest_failures should have both (or up to 6)
    failure_types = [f["event_type"] for f in d["latest_failures"]]
    assert "today.fail" in failure_types
    assert "yest.fail" in failure_types


@pytest.mark.asyncio
async def test_latest_agent_heartbeats_deduplication(client: AsyncClient, session):
    site = Site(code="SITE_TEST", name="Site Test", description="Site for test")
    session.add(site)
    await session.flush()

    now = datetime.now(timezone.utc)
    # 5 heartbeats for Agent A
    for i in range(5):
        session.add(AgentHeartbeat(
            site_id=site.id,
            agent_name="AgentA",
            internet_ok=True,
            received_at=now - timedelta(minutes=10 - i),
        ))
    # 1 older heartbeat for Agent B
    session.add(AgentHeartbeat(
        site_id=site.id,
        agent_name="AgentB",
        internet_ok=True,
        received_at=now - timedelta(hours=5),
    ))
    await session.commit()

    from app.health.repository import latest_agent_heartbeats
    rows = await latest_agent_heartbeats(session)
    agent_names = [h.agent_name for h, s in rows if s.code == "SITE_TEST"]
    assert len(agent_names) == 2
    assert "AgentA" in agent_names
    assert "AgentB" in agent_names
