import httpx

from app.connectors.builtin.onec.client import OneCHTTPClient
from app.connectors.builtin.onec_connector import OneCConnector
from app.sdk.types import ConnectorContext
from app.xml_bridge.parser import XMLBridgeError, parse_xml_safe


async def _install_onec_package(client):
    response = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert response.status_code == 200, response.text


async def test_xml_inbound_json_creates_message_event_and_timeline(client):
    await _install_onec_package(client)
    response = await client.post(
        "/api/onec/xml/inbound",
        json={
            "source_system": "1C UPD",
            "target_system": "1C ERP",
            "message_type": "UPD",
            "correlation_id": "upd-1",
            "xml": "<Документ><Номер>UPD-1</Номер></Документ>",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["message_id"]
    assert body["event_id"]

    messages = (await client.get("/api/onec/xml/messages")).json()
    message = messages[0]
    assert message["status"] == "routed"
    assert message["payload_sha256"]
    assert message["payload_size_bytes"] > 0

    timeline = (await client.get(f"/api/events/{body['event_id']}/timeline")).json()
    assert timeline["event"]["event_type"] == "OneCXmlReceived"
    step_names = [step["step_name"] for step in timeline["runs"][0]["steps"]]
    assert {"receive", "save_integration_message", "parse_xml", "route_by_rule"}.issubset(step_names)
    parse_step = next(step for step in timeline["runs"][0]["steps"] if step["step_name"] == "parse_xml")
    artifact_names = {artifact["name"] for artifact in parse_step["artifacts"]}
    assert {"raw_xml.xml", "parsed_xml.json"}.issubset(artifact_names)


async def test_xml_inbound_raw_headers_and_invalid_xml_are_traceable(client):
    await _install_onec_package(client)
    response = await client.post(
        "/api/onec/xml/inbound",
        content=b"<root><broken></root>",
        headers={"Content-Type": "application/xml", "X-OMH-Source-System": "1C UPD", "X-OMH-Message-Type": "UPD"},
    )

    assert response.status_code == 200
    body = response.json()
    timeline = (await client.get(f"/api/events/{body['event_id']}/timeline")).json()
    assert timeline["event"]["status"] == "failed"
    failed_step = next(step for step in timeline["runs"][0]["steps"] if step["status"] == "failed")
    assert failed_step["error_code"] == "XML_PARSE_FAILED"
    message = (await client.get(f"/api/onec/xml/messages/{body['message_id']}")).json()
    assert message["status"] == "failed"


async def test_xml_parser_blocks_xxe_and_large_payload():
    try:
        parse_xml_safe("<!DOCTYPE foo [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><foo>&xxe;</foo>")
    except XMLBridgeError as exc:
        assert exc.code == "XML_UNSAFE"
    else:
        raise AssertionError("XXE payload must be rejected")

    try:
        parse_xml_safe("<root>too big</root>", max_size_bytes=4)
    except XMLBridgeError as exc:
        assert exc.code == "XML_TOO_LARGE"
    else:
        raise AssertionError("oversized XML must be rejected")


async def test_operation_template_presets_and_crud(client):
    installed = await client.post("/api/operation-templates/install-presets")
    assert installed.status_code == 200
    operations = {item["operation"] for item in installed.json()}
    assert {"receive_upd_xml", "lookup_contractor_by_inn", "update_shipment_status", "print_zpl"}.issubset(operations)

    created = await client.post(
        "/api/operation-templates",
        json={"name": "Custom 1C Op", "system_type": "onec", "operation": "custom", "request_template_json": {"payload": "{{payload}}"}},
    )
    assert created.status_code == 200
    patched = await client.patch(f"/api/operation-templates/{created.json()['id']}", json={"enabled": False})
    assert patched.status_code == 200
    assert patched.json()["enabled"] is False
    deleted = await client.delete(f"/api/operation-templates/{created.json()['id']}")
    assert deleted.status_code == 204


async def test_onec_raw_xml_body_mode(monkeypatch):
    calls = []

    async def fake_request(self, method, url, *, params=None, json_payload=None, content=None, headers=None):
        calls.append({"method": method, "url": url, "json_payload": json_payload, "content": content, "headers": headers})
        return httpx.Response(200, json={"success": True, "status": "accepted"}), {"method": method, "url": url, "body": {"text_preview": content}}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", fake_request)
    connector = OneCConnector()
    result = await connector.send(
        {
            "http_service_base_url": "https://onec.example.local/hs/omh",
            "operations": {"receive_upd_xml": {"method": "POST", "path": "/xml/inbound", "content_type": "application/xml", "body_mode": "raw_xml"}},
        },
        {"_omh": {"operation": "receive_upd_xml"}, "xml": "<Документ>OK</Документ>"},
        ConnectorContext(),
    )
    assert result.success is True
    assert calls[0]["json_payload"] is None
    assert calls[0]["content"] == "<Документ>OK</Документ>"
    assert calls[0]["headers"] == {"Content-Type": "application/xml"}


async def test_odata_lookup_test_endpoint_extracts_fields(monkeypatch, client):
    await _install_onec_package(client)
    async def fake_request(self, method, url, *, params=None, json_payload=None, headers=None):
        assert params is None
        assert "$filter=%D0%98%D0%9D%D0%9D%20eq%20'1234567890'" in url
        return httpx.Response(200, json={"value": [{"Ref_Key": "uuid-1", "Description": "ООО Ромашка"}]}), {"method": method, "url": url, "params": params}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", fake_request)
    await client.post(
        "/api/connectors",
        json={"name": "1C ERP", "connector_type": "onec", "direction": "bidirectional", "config_json": {"base_url": "https://onec.example.local/odata/standard.odata", "auth": {"type": "none"}}},
    )
    response = await client.post(
        "/api/onec/lookup/test",
        json={"connector_name": "1C ERP", "resource": "Catalog_Контрагенты", "filter_template": "ИНН eq '{inn}'", "input": {"inn": "1234567890"}, "extract": {"contractor_uuid": "Ref_Key"}},
    )
    assert response.status_code == 200
    assert response.json()["extracted"]["contractor_uuid"] == "uuid-1"


async def test_workbench_presets_install_and_print_pipeline_dry_run(client):
    await _install_onec_package(client)
    installed = await client.post("/api/onec-workbench/install-print-pipeline")
    assert installed.status_code == 200

    event = await client.post(
        "/api/events",
        json={
            "source_system": "1C ERP",
            "target_system": None,
            "event_type": "OneCPrintRequest",
            "entity_type": "PRINT_ZPL",
            "entity_id": "print-1",
            "payload": {
                "job_key": "pipeline-print-1",
                "source_system": "1C ERP",
                "source_document_id": "DOC-1",
                "printer": {"name": "Pipeline Zebra", "host": "127.0.0.1", "port": 9100, "dpi": 203},
                "dry_run": True,
                "lines": [{"sequence_no": 1, "code": "010460123456789021ABC", "zpl": "^XA\n^FO0,0\n^FDABC^FS\n^XZ"}],
            },
        },
    )
    assert event.status_code == 200
    timeline = (await client.get(f"/api/events/{event.json()['id']}/timeline")).json()
    assert timeline["event"]["status"] == "success"
    assert any(step["step_name"] == "call_print_operation" for step in timeline["runs"][0]["steps"])
