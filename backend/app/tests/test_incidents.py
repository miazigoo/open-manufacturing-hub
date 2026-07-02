async def test_failed_events_with_same_error_create_one_incident_and_increment_count(client, failed_payload):
    await client.post("/api/events", json=failed_payload)
    payload2 = dict(failed_payload)
    payload2["entity_id"] = "1533"
    payload2["payload"] = dict(failed_payload["payload"], order_id="1533")
    await client.post("/api/events", json=payload2)

    incidents = (await client.get("/api/incidents")).json()
    assert len(incidents) == 1
    assert incidents[0]["error_code"] == "WAREHOUSE_NOT_FOUND"
    assert incidents[0]["affected_events_count"] == 2


async def test_different_error_code_creates_different_incident(client, failed_payload):
    await client.post("/api/events", json=failed_payload)
    invalid = dict(failed_payload)
    invalid["payload"] = {"order_id": "1534", "warehouse_id": "MAIN"}
    await client.post("/api/events", json=invalid)

    incidents = (await client.get("/api/incidents")).json()
    assert {incident["error_code"] for incident in incidents} == {"WAREHOUSE_NOT_FOUND", "VALIDATION_FAILED"}


async def test_acknowledge_and_resolve_change_incident_status(client, failed_payload):
    await client.post("/api/events", json=failed_payload)
    incident = (await client.get("/api/incidents")).json()[0]

    acknowledged = (await client.post(f"/api/incidents/{incident['id']}/acknowledge")).json()
    assert acknowledged["status"] == "acknowledged"

    resolved = (await client.post(f"/api/incidents/{incident['id']}/resolve")).json()
    assert resolved["status"] == "resolved"
