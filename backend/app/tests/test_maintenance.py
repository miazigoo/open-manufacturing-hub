from datetime import datetime, timedelta, timezone


async def test_active_maintenance_prevents_send_and_incident(client, failed_payload):
    now = datetime.now(timezone.utc)
    await client.post(
        "/api/maintenance",
        json={
            "component_type": "connector",
            "component_name": "Mock WMS",
            "reason": "Mock WMS maintenance",
            "starts_at": (now - timedelta(minutes=5)).isoformat(),
            "ends_at": (now + timedelta(hours=1)).isoformat(),
        },
    )

    event = (await client.post("/api/events", json=failed_payload)).json()
    assert event["status"] == "retry_waiting"

    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    guard_step = next(step for step in timeline["runs"][0]["steps"] if step["step_name"] == "maintenance_guard")
    assert guard_step["status"] == "skipped"
    assert any(artifact["artifact_type"] == "maintenance" for artifact in guard_step["artifacts"])
    assert (await client.get("/api/incidents")).json() == []
