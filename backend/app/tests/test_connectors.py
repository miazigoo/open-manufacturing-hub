from app.connectors.builtin.mock_wms_connector import MockWMSConnector
from app.connectors.builtin.rest_connector import RESTConnector
from app.connectors.registry import registry
from app.sdk.exceptions import ConnectorNotFoundError
from app.sdk.types import ConnectorContext


async def test_builtin_connectors_are_registered():
    types = {item.connector_type for item in registry.list()}
    assert {"rest", "webhook", "mock_erp", "mock_wms", "onec"}.issubset(types)
    try:
        registry.get("missing")
    except ConnectorNotFoundError:
        pass
    else:
        raise AssertionError("unknown connector should raise")


async def test_connector_instance_crud_health_enable_disable(client):
    response = await client.post(
        "/api/connectors",
        json={"name": "REST Test", "connector_type": "rest", "direction": "target", "config_json": {"method": "POST", "url": "https://example.com/orders"}},
    )
    assert response.status_code == 200
    connector = response.json()

    validation = await client.post(f"/api/connectors/{connector['id']}/test-config")
    assert validation.status_code == 200
    assert validation.json()["valid"] is True

    health = await client.post(f"/api/connectors/{connector['id']}/healthcheck")
    assert health.status_code == 200
    assert health.json()["status"] in {"unknown", "warning", "ok"}

    disabled = (await client.post(f"/api/connectors/{connector['id']}/disable")).json()
    assert disabled["enabled"] is False
    enabled = (await client.post(f"/api/connectors/{connector['id']}/enable")).json()
    assert enabled["enabled"] is True


async def test_mock_wms_connector_send_and_dry_run():
    connector = MockWMSConnector()
    config = {"fail_warehouse_ids": ["005"], "success_warehouse_ids": ["MAIN"]}
    failed = await connector.send(config, {"warehouse_id": "005"}, ConnectorContext())
    assert failed.success is False
    assert failed.error_code == "WAREHOUSE_NOT_FOUND"
    ok = await connector.send(config, {"warehouse_id": "MAIN", "target_order_id": "1532"}, ConnectorContext())
    assert ok.success is True
    assert ok.response_payload["external_document_id"] == "WMS-SHIP-1532"
    dry = await connector.dry_run_send(config, {"warehouse_id": "005"}, ConnectorContext(dry_run=True))
    assert dry.success is True
    assert dry.response_payload["dry_run"] is True


async def test_rest_connector_dry_run_and_invalid_url_validation():
    connector = RESTConnector()
    invalid = await connector.validate_config({"method": "POST", "url": "not-a-url"})
    assert invalid.valid is False
    dry = await connector.dry_run_send({"method": "POST", "url": "https://example.com/orders"}, {"order_id": "1"}, ConnectorContext(dry_run=True))
    assert dry.success is True
    assert dry.request_payload["url"] == "https://example.com/orders"


async def test_webhook_connector_endpoint_creates_event(client):
    created = await client.post(
        "/api/connectors",
        json={
            "name": "Webhook Demo Source",
            "connector_type": "webhook",
            "direction": "source",
            "config_json": {"default_source_system": "External Webhook", "default_target_system": "Mock WMS"},
        },
    )
    assert created.status_code == 200
    response = await client.post(
        "/api/webhooks/Webhook Demo Source",
        json={"event_type": "SalesOrderCreated", "entity_type": "SalesOrder", "entity_id": "W-1", "payload": {"order_id": "W-1", "warehouse_id": "MAIN", "items": []}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["event_id"]
    assert body["status"] == "success"


async def test_pipeline_missing_connector_fails_with_clear_error(client, success_payload):
    payload = dict(success_payload)
    payload["target_system"] = "Missing WMS"
    response = await client.post("/api/events", json=payload)
    assert response.status_code == 200
    event = response.json()
    assert event["status"] == "failed"
    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    failed_step = next(step for step in timeline["runs"][0]["steps"] if step["status"] == "failed")
    assert failed_step["step_name"] == "call_connector"
    assert failed_step["error_code"] == "CONNECTOR_NOT_FOUND"


async def test_connector_instance_maintenance_skips_send_without_incident(client, success_payload):
    connectors = (await client.get("/api/connectors")).json()
    mock_wms = next(connector for connector in connectors if connector["name"] == "Mock WMS")
    patched = await client.patch(f"/api/connectors/{mock_wms['id']}", json={"status": "maintenance"})
    assert patched.status_code == 200

    response = await client.post("/api/events", json=success_payload)
    assert response.status_code == 200
    event = response.json()
    assert event["status"] == "retry_waiting"
    timeline = (await client.get(f"/api/events/{event['id']}/timeline")).json()
    guard_step = next(step for step in timeline["runs"][0]["steps"] if step["step_name"] == "maintenance_guard")
    assert guard_step["status"] == "skipped"
    assert any(artifact["artifact_type"] == "maintenance" for artifact in guard_step["artifacts"])
    assert (await client.get("/api/incidents")).json() == []
