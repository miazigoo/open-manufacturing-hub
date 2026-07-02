from app.core.enums import ArtifactType, EventStatus, RunStatus, StepStatus


async def test_event_creation_creates_run_steps_and_artifacts(client, success_payload):
    response = await client.post("/api/events", json=success_payload)
    assert response.status_code == 200
    event = response.json()
    assert event["status"] == EventStatus.SUCCESS

    timeline_response = await client.get(f"/api/events/{event['id']}/timeline")
    assert timeline_response.status_code == 200
    timeline = timeline_response.json()
    assert len(timeline["runs"]) == 1
    run = timeline["runs"][0]
    assert run["run_number"] == 1
    assert run["status"] == RunStatus.SUCCESS
    assert [step["step_name"] for step in run["steps"]] == [
        "receive",
        "normalize",
        "validate",
        "map_to_target",
        "send_to_target",
        "handle_response",
    ]
    assert sum(len(step["artifacts"]) for step in run["steps"]) > 0


async def test_failed_pipeline_marks_send_step_failed_and_saves_error_artifact(client, failed_payload):
    response = await client.post("/api/events", json=failed_payload)
    assert response.status_code == 200
    event = response.json()
    assert event["status"] == EventStatus.FAILED

    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    run = timeline["runs"][0]
    assert run["status"] == RunStatus.FAILED
    failed_step = run["steps"][-1]
    assert failed_step["step_name"] == "send_to_target"
    assert failed_step["status"] == StepStatus.FAILED
    assert failed_step["error_code"] == "WAREHOUSE_NOT_FOUND"
    assert any(a["artifact_type"] == ArtifactType.ERROR_DETAILS for a in failed_step["artifacts"])


async def test_successful_pipeline(client, success_payload):
    response = await client.post("/api/events", json=success_payload)
    assert response.status_code == 200
    assert response.json()["status"] == EventStatus.SUCCESS
