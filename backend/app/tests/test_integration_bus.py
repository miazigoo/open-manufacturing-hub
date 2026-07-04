import hashlib

import httpx

from app.connectors.builtin.onec.client import OneCHTTPClient


async def _workflow(client, name="Bus Test Workflow", steps=None, event_type="BusRequestReceived"):
    response = await client.post(
        "/api/workflows",
        json={
            "name": name,
            "event_type": event_type,
            "steps_json": steps or [{"name": "receive"}, {"name": "call_connector"}, {"name": "handle_response"}],
            "validation_json": {"required_fields": []},
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_bus_endpoint_static_token_sync_response_and_timeline(client):
    workflow = await _workflow(client)
    endpoint = await client.post(
        "/api/integration-bus/endpoints",
        json={
            "name": "1C status to WMS",
            "slug": "onec-status-to-wms",
            "input_mode": "json",
            "response_mode": "sync_response",
            "default_source_system": "1C ERP",
            "default_target_system": "Mock WMS",
            "default_event_type": "BusRequestReceived",
            "workflow_id": workflow["id"],
            "auth_mode": "static_token",
            "auth_config_json": {"token": "secret"},
        },
    )
    assert endpoint.status_code == 200

    unauthorized = await client.post("/api/bus/in/onec-status-to-wms", json={"warehouse_id": "MAIN"})
    assert unauthorized.status_code == 400
    assert unauthorized.json()["detail"] == "BUS_AUTH_FAILED"

    response = await client.post(
        "/api/bus/in/onec-status-to-wms",
        headers={"X-OMH-Token": "secret"},
        json={"warehouse_id": "MAIN", "target_order_id": "SO-1", "items": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["event_id"]
    assert body["response"]["external_document_id"] == "WMS-SHIP-SO-1"
    timeline = (await client.get(f"/api/events/{body['event_id']}/timeline")).json()
    assert timeline["event"]["status"] == "success"


async def test_bus_disabled_endpoint_and_missing_slug_errors(client):
    workflow = await _workflow(client, name="Disabled Bus Workflow")
    endpoint = await client.post(
        "/api/integration-bus/endpoints",
        json={"name": "Disabled endpoint", "slug": "disabled-endpoint", "enabled": False, "input_mode": "json", "response_mode": "accepted_event", "default_event_type": "DisabledBus", "workflow_id": workflow["id"]},
    )
    assert endpoint.status_code == 200
    disabled = await client.post("/api/bus/in/disabled-endpoint", json={})
    assert disabled.status_code == 400
    assert disabled.json()["detail"] == "BUS_ENDPOINT_DISABLED"
    missing = await client.post("/api/bus/in/missing-endpoint", json={})
    assert missing.status_code == 404


async def test_bus_route_priority_selects_best_route(client):
    workflow = await _workflow(client, name="Route Priority Workflow", steps=[{"name": "receive"}], event_type="RoutePriority")
    low = await client.post("/api/integration-bus/routes", json={"name": "Low priority route", "event_type": "RoutePriority", "workflow_id": workflow["id"], "priority": 200})
    high = await client.post("/api/integration-bus/routes", json={"name": "High priority route", "event_type": "RoutePriority", "workflow_id": workflow["id"], "priority": 10})
    assert low.status_code == 200
    assert high.status_code == 200
    endpoint = await client.post(
        "/api/integration-bus/endpoints",
        json={"name": "Route priority endpoint", "slug": "route-priority", "input_mode": "json", "response_mode": "accepted_event", "default_event_type": "RoutePriority"},
    )
    assert endpoint.status_code == 200
    response = await client.post("/api/bus/in/route-priority", json={"payload": {"id": "1"}})
    assert response.status_code == 200
    assert response.json()["route_id"] == high.json()["id"]


async def test_bus_xml_endpoint_stores_message_hash_and_preview(client):
    workflow = await _workflow(client, name="XML Bus Workflow", steps=[{"name": "receive"}], event_type="OneCXmlReceived")
    endpoint = await client.post(
        "/api/integration-bus/endpoints",
        json={"name": "UPD XML bus", "slug": "bus-upd-xml", "input_mode": "xml", "response_mode": "accepted_message", "default_source_system": "1C UPD", "default_target_system": "1C ERP", "default_event_type": "OneCXmlReceived", "default_entity_type": "UPD", "workflow_id": workflow["id"]},
    )
    assert endpoint.status_code == 200
    xml = "<Документ><Номер>UPD-42</Номер></Документ>"
    response = await client.post("/api/bus/in/bus-upd-xml", content=xml.encode(), headers={"Content-Type": "application/xml"})
    assert response.status_code == 200
    body = response.json()
    assert body["message_id"]
    message = (await client.get(f"/api/onec/xml/messages/{body['message_id']}")).json()
    assert message["payload_sha256"] == hashlib.sha256(xml.encode()).hexdigest()
    assert message["payload_json"]["forward_mode"] == "raw_forward"
    assert message["payload_json"]["preview"].startswith("<Документ>")


async def test_odata_lookup_template_crud_test_and_step(monkeypatch, client):
    async def fake_request(self, method, url, *, params=None, json_payload=None):
        assert params["$filter"] == "ИНН eq '1234567890'"
        return httpx.Response(200, json={"value": [{"Ref_Key": "uuid-1", "Description": "ООО Ромашка"}]}), {"method": method, "url": url, "params": params}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", fake_request)
    connector = await client.post(
        "/api/connectors",
        json={"name": "1C ERP", "connector_type": "onec", "direction": "bidirectional", "config_json": {"base_url": "https://onec.example.local/odata/standard.odata", "auth": {"type": "none"}}},
    )
    assert connector.status_code == 200
    template = await client.post(
        "/api/odata-lookups",
        json={"name": "Find contractor by INN", "connector_id": connector.json()["id"], "resource": "Catalog_Контрагенты", "filter_template": "ИНН eq '{inn}'", "extract_json": {"contractor_uuid": "Ref_Key", "contractor_name": "Description"}},
    )
    assert template.status_code == 200
    tested = await client.post(f"/api/odata-lookups/{template.json()['id']}/test", json={"input": {"inn": "1234567890"}})
    assert tested.status_code == 200
    assert tested.json()["extracted"]["contractor_uuid"] == "uuid-1"

    workflow = await _workflow(client, name="Lookup Template Workflow", steps=[{"name": "receive"}, {"name": "odata_lookup", "config": {"template": "Find contractor by INN", "input": {"inn": "payload.inn"}, "inject": {"payload.contractor_uuid": "contractor_uuid"}}}, {"name": "handle_response"}], event_type="LookupTemplate")
    endpoint = await client.post("/api/integration-bus/endpoints", json={"name": "Lookup endpoint", "slug": "lookup-template", "input_mode": "json", "response_mode": "sync_response", "default_event_type": "LookupTemplate", "workflow_id": workflow["id"]})
    assert endpoint.status_code == 200
    response = await client.post("/api/bus/in/lookup-template", json={"inn": "1234567890"})
    assert response.status_code == 200
    timeline = (await client.get(f"/api/events/{response.json()['event_id']}/timeline")).json()
    lookup_step = next(step for step in timeline["runs"][0]["steps"] if step["step_name"] == "odata_lookup")
    result_artifact = next(artifact for artifact in lookup_step["artifacts"] if artifact["name"] == "odata_lookup_result.json")
    assert result_artifact["content_json"]["contractor_uuid"] == "uuid-1"


async def test_bus_presets_and_print_endpoint(client):
    presets = await client.post("/api/integration-bus/install-presets")
    assert presets.status_code == 200
    slugs = {endpoint["slug"] for endpoint in presets.json()["endpoints"]}
    assert {"onec-to-site", "site-contractor-lookup", "upd-xml", "print-zpl"}.issubset(slugs)

    response = await client.post(
        "/api/bus/in/print-zpl",
        json={
            "job_key": "bus-print-1",
            "source_system": "1C ERP",
            "source_document_id": "DOC-1",
            "printer": {"name": "Bus Zebra", "host": "127.0.0.1", "port": 9100, "dpi": 203},
            "dry_run": True,
            "lines": [{"sequence_no": 1, "code": "010460123456789021ABC", "zpl": "^XA\n^FO0,0\n^FDABC^FS\n^XZ"}],
        },
    )
    assert response.status_code == 200
    timeline = (await client.get(f"/api/events/{response.json()['event_id']}/timeline")).json()
    assert timeline["event"]["status"] == "success"
    assert any(step["step_name"] == "call_print_operation" for step in timeline["runs"][0]["steps"])

    existing = await client.post(
        "/api/printing/onec/send-batch",
        json={
            "job_key": "existing-print-still-works",
            "source_system": "1C ERP",
            "printer": {"name": "Existing Zebra", "host": "127.0.0.1", "port": 9100, "dpi": 203},
            "dry_run": True,
            "lines": [{"sequence_no": 1, "code": "010460123456789021DEF", "zpl": "^XA\n^FO0,0\n^FDDEF^FS\n^XZ"}],
        },
    )
    assert existing.status_code == 200
    assert existing.json()["sent"] == 1
