import httpx

from app.connectors.builtin.onec.client import OneCHTTPClient


def shipment_fact(order_id: str = "1532"):
    return {
        "shipment_id": f"WMS-SHIP-{order_id}",
        "order_id": order_id,
        "status": "shipped",
        "warehouse_id": "MAIN",
        "items": [{"sku": "ABC123", "qty": 5}],
    }


async def test_mock_onec_http_service(client):
    health = await client.get("/api/mock-onec/hs/omh/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    success = await client.post("/api/mock-onec/hs/omh/shipment-facts", json={"payload": {"external_order_id": "1532"}})
    assert success.status_code == 200
    assert success.json()["external_document_id"] == "1C-SHIP-1532"

    business = await client.post("/api/mock-onec/hs/omh/shipment-facts", json={"payload": {"external_order_id": "404"}})
    assert business.status_code == 200
    assert business.json()["success"] is False
    assert business.json()["error_code"] == "ORDER_NOT_FOUND"

    server = await client.post("/api/mock-onec/hs/omh/shipment-facts", json={"payload": {"external_order_id": "500"}})
    assert server.status_code == 500


async def test_shipment_fact_mapping_preset(client):
    installed = await client.post("/api/mappings/presets/install")
    assert installed.status_code == 200
    mappings = installed.json()
    mapping = next(item for item in mappings if item["name"] == "mock_wms_shipment_fact_to_onec_shipment_fact")
    response = await client.post(f"/api/mappings/{mapping['id']}/versions/1/execute", json={"payload": shipment_fact()})
    assert response.status_code == 200
    output = response.json()["output"]
    assert output["_omh"]["operation"] == "update_shipment_status"
    assert output["omh"]["event_type"] == "ShipmentFactCreated"
    assert output["payload"]["external_order_id"] == "1532"
    assert output["payload"]["items"][0]["quantity"] == 5


async def test_bidirectional_scenario_installer_is_idempotent(client):
    first = await client.post("/api/onec-scenarios/install-bidirectional-demo")
    second = await client.post("/api/onec-scenarios/install-bidirectional-demo")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["workflow_id"] == second.json()["workflow_id"]
    assert first.json()["target_connector_id"] == second.json()["target_connector_id"]
    assert first.json()["mappings"] == ["mock_wms_shipment_fact_to_onec_shipment_fact"]


async def test_bidirectional_workflow_success_and_incidents(monkeypatch, client):
    async def fake_request(self, method, url, *, params=None, json_payload=None):
        order_id = json_payload["payload"]["external_order_id"]
        if order_id == "404":
            return httpx.Response(200, json={"success": False, "error_code": "ORDER_NOT_FOUND", "error_message": "Order 404 was not found in 1C"}), {"method": method, "url": url, "body": json_payload}, None, None
        if order_id == "500":
            return httpx.Response(500, json={"error": "Internal 1C error"}), {"method": method, "url": url, "body": json_payload}, None, None
        return httpx.Response(200, json={"success": True, "external_document_id": f"1C-SHIP-{order_id}", "status": "accepted"}), {"method": method, "url": url, "body": json_payload}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", fake_request)
    await client.post("/api/onec-scenarios/install-bidirectional-demo")

    success = await client.post("/api/onec-scenarios/test-shipment-fact", json=shipment_fact("1532"))
    assert success.status_code == 200
    success_event_id = success.json()["event_id"]
    success_timeline = (await client.get(f"/api/events/{success_event_id}/timeline")).json()
    assert success_timeline["event"]["status"] == "success"
    call_step = next(step for step in success_timeline["runs"][0]["steps"] if step["step_name"] == "call_connector")
    outgoing = next(artifact for artifact in call_step["artifacts"] if artifact["artifact_type"] == "outgoing_request")
    assert outgoing["content_json"]["body"]["payload"]["external_order_id"] == "1532"

    business = await client.post("/api/onec-scenarios/test-shipment-fact", json=shipment_fact("404"))
    business_event_id = business.json()["event_id"]
    business_timeline = (await client.get(f"/api/events/{business_event_id}/timeline")).json()
    assert business_timeline["event"]["status"] == "failed"
    failed_step = next(step for step in business_timeline["runs"][0]["steps"] if step["status"] == "failed")
    assert failed_step["error_code"] == "ORDER_NOT_FOUND"

    technical = await client.post("/api/onec-scenarios/test-shipment-fact", json=shipment_fact("500"))
    technical_event_id = technical.json()["event_id"]
    technical_timeline = (await client.get(f"/api/events/{technical_event_id}/timeline")).json()
    failed_step = next(step for step in technical_timeline["runs"][0]["steps"] if step["status"] == "failed")
    assert failed_step["error_code"] == "ONEC_HTTP_SERVICE_ERROR"

    incidents = (await client.get("/api/incidents")).json()
    error_codes = {incident["error_code"] for incident in incidents}
    assert {"ORDER_NOT_FOUND", "ONEC_HTTP_SERVICE_ERROR"}.issubset(error_codes)
