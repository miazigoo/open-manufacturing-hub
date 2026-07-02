from app.core.enums import ArtifactType, RunMode, RunStatus


async def test_full_replay_creates_new_run_with_parent_and_incremented_number(client, failed_payload):
    event = (await client.post("/api/events", json=failed_payload)).json()
    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    first_run_id = timeline["runs"][0]["id"]

    replay = await client.post(f"/api/events/{event['id']}/replay")
    assert replay.status_code == 200
    replay_run = replay.json()
    assert replay_run["mode"] == RunMode.REPLAY
    assert replay_run["run_number"] == 2
    assert replay_run["parent_run_id"] == first_run_id


async def test_edit_replay_saves_edited_artifact_and_succeeds(client, failed_payload):
    event = (await client.post("/api/events", json=failed_payload)).json()
    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    raw_artifact = timeline["runs"][0]["steps"][0]["artifacts"][0]

    edited = dict(raw_artifact["content_json"])
    edited["warehouse_id"] = "MAIN"
    response = await client.post(
        f"/api/artifacts/{raw_artifact['id']}/edit-replay",
        json={"edited_content": edited, "start_from_step": "validate"},
    )
    assert response.status_code == 200
    run = response.json()
    assert run["mode"] == RunMode.EDIT_REPLAY
    assert run["status"] == RunStatus.SUCCESS

    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    latest = timeline["runs"][-1]
    assert latest["run_number"] == 2
    assert any(a["name"].startswith("edited_") for a in latest["artifacts"])


async def test_dry_run_saves_dry_run_request_without_external_send(client, failed_payload):
    event = (await client.post("/api/events", json=failed_payload)).json()
    response = await client.post(f"/api/events/{event['id']}/dry-run")
    assert response.status_code == 200
    run = response.json()
    assert run["mode"] == RunMode.DRY_RUN
    assert run["status"] == RunStatus.DRY_RUN_SUCCESS

    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    dry_run = timeline["runs"][-1]
    send_step = next(step for step in dry_run["steps"] if step["step_name"] == "send_to_target")
    artifact_types = {artifact["artifact_type"] for artifact in send_step["artifacts"]}
    assert ArtifactType.DRY_RUN_REQUEST in artifact_types
    assert ArtifactType.OUTGOING_REQUEST not in artifact_types

    event_after_dry_run = (await client.get(f"/api/events/{event['id']}")).json()
    assert event_after_dry_run["status"] == "failed"
