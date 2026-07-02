from app.notifications import channels
from app.pipeline import steps


async def test_notification_channel_exception_does_not_break_event_creation(client, failed_payload, monkeypatch):
    async def broken_webhook(url, payload):
        raise RuntimeError("webhook transport exploded")

    monkeypatch.setattr(channels, "send_webhook", broken_webhook)
    await client.post(
        "/api/notifications/rules",
        json={
            "name": "Broken webhook",
            "trigger_type": "incident_created",
            "channels": [{"type": "webhook", "url": "https://example.com/broken"}],
        },
    )

    response = await client.post("/api/events", json=failed_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "failed"

    deliveries = (await client.get("/api/notifications/deliveries")).json()
    assert deliveries[0]["status"] == "failed"
    assert "webhook transport exploded" in deliveries[0]["error_message"]


async def test_unknown_replay_step_returns_400(client, failed_payload):
    event = (await client.post("/api/events", json=failed_payload)).json()
    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    run_id = timeline["runs"][0]["id"]

    response = await client.post(f"/api/runs/{run_id}/replay-from-step", json={"step_name": "missing_step"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown step: missing_step"


async def test_unexpected_pipeline_exception_is_persisted_as_failed_event(client, success_payload, monkeypatch):
    def broken_map(payload):
        raise RuntimeError("mapper unavailable")

    monkeypatch.setattr(steps, "map_to_target", broken_map)
    response = await client.post("/api/events", json=success_payload)
    assert response.status_code == 200
    event = response.json()
    assert event["status"] == "failed"

    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    failed_step = timeline["runs"][0]["steps"][-1]
    assert failed_step["step_name"] == "map_to_target"
    assert failed_step["error_code"] == "UNEXPECTED_PIPELINE_ERROR"
    assert any(artifact["name"] == "unexpected_error_details.json" for artifact in failed_step["artifacts"])
