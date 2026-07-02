from datetime import datetime, timedelta, timezone

from app.core.enums import EventStatus, RunMode, RunStatus
from app.execution.exceptions import StepNotFoundError
from app.execution.registry import registry


async def test_execution_step_registry_lists_builtin_steps(client):
    assert registry.get("receive").display_name == "Receive Event"
    assert registry.get("send_to_target").name == "call_connector"
    try:
        registry.get("missing_step")
        raise AssertionError("missing step did not raise")
    except StepNotFoundError as exc:
        assert "missing_step" in str(exc)

    response = await client.get("/api/execution/steps")
    assert response.status_code == 200
    names = {step["name"] for step in response.json()}
    assert {"receive", "maintenance_guard", "map_payload", "call_connector", "create_incident", "send_notifications"} <= names


async def test_default_execution_workflow_runs_failure_steps(client, failed_payload):
    event = (await client.post("/api/events", json=failed_payload)).json()
    assert event["status"] == EventStatus.FAILED
    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    steps = timeline["runs"][0]["steps"]
    assert [step["step_name"] for step in steps][-3:] == ["call_connector", "create_incident", "send_notifications"]
    assert next(step for step in steps if step["step_name"] == "call_connector")["status"] == "failed"
    assert next(step for step in steps if step["step_name"] == "create_incident")["status"] == "success"


async def test_workflow_selection_priority_exact_event_type_default(client, success_payload):
    default_workflow = await client.post(
        "/api/workflows",
        json={"name": "Default wildcard", "event_type": None, "steps_json": [{"name": "receive"}]},
    )
    assert default_workflow.status_code == 200
    event_type_workflow = await client.post(
        "/api/workflows",
        json={"name": "Sales order type route", "event_type": "SalesOrderCreated", "steps_json": [{"name": "receive"}, {"name": "normalize"}]},
    )
    assert event_type_workflow.status_code == 200
    exact_workflow = await client.post(
        "/api/workflows",
        json={
            "name": "Exact ERP WMS route",
            "event_type": "SalesOrderCreated",
            "source_system": "Mock ERP",
            "target_system": "Mock WMS",
            "steps_json": [{"name": "receive"}, {"name": "normalize"}, {"name": "validate"}],
        },
    )
    assert exact_workflow.status_code == 200

    exact_event = (await client.post("/api/events", json=success_payload)).json()
    exact_timeline = (await client.get(f"/api/events/{exact_event['id']}/timeline")).json()
    assert exact_timeline["runs"][0]["workflow_name"] == "Exact ERP WMS route"

    type_payload = dict(success_payload, source_system="Other ERP")
    type_event = (await client.post("/api/events", json=type_payload)).json()
    type_timeline = (await client.get(f"/api/events/{type_event['id']}/timeline")).json()
    assert type_timeline["runs"][0]["workflow_name"] == "Sales order type route"

    fallback_payload = dict(success_payload, event_type="InventoryAdjusted", source_system="Other ERP")
    fallback_event = (await client.post("/api/events", json=fallback_payload)).json()
    fallback_timeline = (await client.get(f"/api/events/{fallback_event['id']}/timeline")).json()
    assert fallback_timeline["runs"][0]["workflow_name"] == "Default wildcard"


async def test_execution_engine_replay_from_step_and_dry_run(client, failed_payload):
    event = (await client.post("/api/events", json=failed_payload)).json()
    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    run_id = timeline["runs"][0]["id"]

    replay = await client.post(f"/api/runs/{run_id}/replay-from-step", json={"step_name": "call_connector"})
    assert replay.status_code == 200
    replay_run = replay.json()
    assert replay_run["mode"] == RunMode.REPLAY_FROM_STEP
    assert replay_run["steps"][0]["step_name"] == "call_connector"

    dry_run = await client.post(f"/api/events/{event['id']}/dry-run")
    assert dry_run.status_code == 200
    body = dry_run.json()
    assert body["status"] == RunStatus.DRY_RUN_SUCCESS
    assert next(step for step in body["steps"] if step["step_name"] == "call_connector")["status"] == "dry_run"


async def test_maintenance_guard_retries_without_incident(client, failed_payload):
    now = datetime.now(timezone.utc)
    await client.post(
        "/api/maintenance",
        json={
            "component_type": "connector",
            "component_name": "Mock WMS",
            "reason": "Planned maintenance",
            "starts_at": (now - timedelta(minutes=1)).isoformat(),
            "ends_at": (now + timedelta(minutes=30)).isoformat(),
        },
    )
    event = (await client.post("/api/events", json=failed_payload)).json()
    assert event["status"] == EventStatus.RETRY_WAITING
    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    steps = timeline["runs"][0]["steps"]
    assert steps[-1]["step_name"] == "maintenance_guard"
    assert steps[-1]["status"] == "skipped"
    assert not any(step["step_name"] == "create_incident" for step in steps)
    assert (await client.get("/api/incidents")).json() == []
