async def test_demo_seed_endpoint_creates_meaningful_demo_data(client):
    response = await client.post("/api/demo/seed")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

    events = (await client.get("/api/events")).json()
    by_entity = {event["entity_id"]: event for event in events}
    assert by_entity["1001"]["status"] == "success"
    assert by_entity["1532"]["status"] == "failed"

    edit_event = by_entity["1701"]
    timeline = (await client.get(f"/api/events/{edit_event['id']}/timeline")).json()
    assert [run["mode"] for run in timeline["runs"]] == ["normal", "edit_replay"]
    assert timeline["runs"][-1]["status"] == "success"

    incidents = (await client.get("/api/incidents")).json()
    grouped = next(incident for incident in incidents if incident["target_system"] == "Mock WMS")
    assert grouped["error_code"] == "WAREHOUSE_NOT_FOUND"
    assert grouped["affected_events_count"] == 5

    health = (await client.get("/api/health/dashboard")).json()
    site = next(site for site in health["sites"] if site["name"] == "Main Warehouse")
    assert site["internet"] == "down"
    assert site["wms"] == "warning"
    assert site["erp"] == "ok"
    assert site["queue_size"] == 342

    rules = (await client.get("/api/notifications/rules")).json()
    assert any(rule["name"] == "Critical WMS errors" for rule in rules)

    connectors = (await client.get("/api/connectors")).json()
    connector_names = {connector["name"] for connector in connectors}
    assert {"Mock ERP", "Mock WMS", "REST Demo Target", "Webhook Demo Source"}.issubset(connector_names)

    maintenance = (await client.get("/api/maintenance")).json()
    assert any(window["component_name"] == "Mock WMS" and window["enabled"] for window in maintenance)

    retention = (await client.get("/api/retention/preview")).json()
    assert retention["expired_events"] >= 1
    assert retention["pinned_skipped"] >= 1
