import httpx

from app.connectors.builtin.onec.client import OneCHTTPClient


async def test_scenario_library_preview_install_and_designer_build(client):
    scenarios = await client.get("/api/scenario-library")
    assert scenarios.status_code == 200
    assert {item["code"] for item in scenarios.json()} >= {"onec_xml_raw_bridge", "onec_to_printer"}

    preview = await client.post("/api/scenario-library/onec_xml_raw_bridge/preview")
    assert preview.status_code == 200
    assert preview.json()["will_create"]["endpoints"] == 1

    install = await client.post("/api/scenario-library/onec_xml_raw_bridge/install", json={"endpoint_slug": "test-upd-xml"})
    assert install.status_code == 200, install.text
    installed = install.json()
    assert installed["endpoint_url"] == "/api/bus/in/test-upd-xml"
    assert installed["test_case_id"]
    assert "HTTPСоединение" in installed["onec_http_example"]

    reinstall = await client.post("/api/scenario-library/onec_xml_raw_bridge/install", json={"endpoint_slug": "test-upd-xml"})
    assert reinstall.status_code == 200
    assert reinstall.json()["endpoint_id"] == installed["endpoint_id"]

    build = await client.post(
        "/api/integration-designer/build",
        json={"scenario_code": "onec_to_printer", "source": {"endpoint_slug": "designer-print-test", "input_mode": "json"}, "target": {"target_system": "Printer"}, "logic": {"response_mode": "accepted_event"}},
    )
    assert build.status_code == 200, build.text
    assert build.json()["created"]["workflow_id"]


async def test_xml_tools_parse_diff_and_paths(client):
    xml = "<Документ><Номер>UPD-1</Номер><ИНН>1234567890</ИНН></Документ>"
    parsed = await client.post("/api/xml-tools/parse", json={"xml": xml})
    assert parsed.status_code == 200
    body = parsed.json()
    assert body["valid"] is True
    assert body["sha256"]
    assert any("Документ" in path for path in body["paths"])

    diff = await client.post("/api/xml-tools/diff", json={"left_xml": xml, "right_xml": xml.replace("UPD-1", "UPD-2")})
    assert diff.status_code == 200
    assert diff.json()["same_hash"] is False
    assert "UPD-2" in diff.json()["diff_text"]


async def test_odata_explorer_resources_query_and_lookup(monkeypatch, client):
    package = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert package.status_code == 200, package.text
    async def fake_request(self, method, url, *, params=None, json_payload=None):
        if url.endswith("$metadata"):
            return httpx.Response(200, text='<Schema><EntitySet Name="Catalog_Контрагенты" /></Schema>'), {"url": url}, None, None
        assert params["$filter"] == "ИНН eq '1234567890'"
        return httpx.Response(200, json={"value": [{"Ref_Key": "uuid-1", "Description": "ООО Ромашка"}]}), {"method": method, "url": url, "params": params}, None, None

    monkeypatch.setattr(OneCHTTPClient, "request", fake_request)
    connector = await client.post("/api/connectors", json={"name": "1C ERP", "connector_type": "onec", "direction": "bidirectional", "config_json": {"base_url": "https://onec.example/odata", "auth": {"type": "none"}}})
    connector_id = connector.json()["id"]

    resources = await client.get(f"/api/odata-explorer/{connector_id}/resources")
    assert resources.status_code == 200
    assert "Catalog_Контрагенты" in resources.json()["resources"]

    query = await client.post(f"/api/odata-explorer/{connector_id}/query", json={"resource": "Catalog_Контрагенты", "top": 1, "filter": "ИНН eq '1234567890'"})
    assert query.status_code == 200
    assert query.json()["items"][0]["Ref_Key"] == "uuid-1"

    lookup = await client.post(f"/api/odata-explorer/{connector_id}/lookups", json={"name": "Explorer contractor lookup", "resource": "Catalog_Контрагенты", "filter_template": "ИНН eq '{inn}'", "extract_json": {"contractor_uuid": "Ref_Key"}})
    assert lookup.status_code == 200
    assert lookup.json()["name"] == "Explorer contractor lookup"


async def test_test_console_saved_case_and_workflow_validation(client):
    workflow = await client.post("/api/workflows", json={"name": "Console workflow", "event_type": "ConsoleEvent", "steps_json": [{"name": "receive"}], "validation_json": {"required_fields": []}})
    assert workflow.status_code == 200
    endpoint = await client.post("/api/integration-bus/endpoints", json={"name": "Console endpoint", "slug": "console-endpoint", "input_mode": "json", "response_mode": "sync_response", "default_event_type": "ConsoleEvent", "workflow_id": workflow.json()["id"]})
    assert endpoint.status_code == 200

    sent = await client.post("/api/test-console/send", json={"endpoint_id": endpoint.json()["id"], "input_mode": "json", "headers_json": {}, "body_json": {"hello": "world"}})
    assert sent.status_code == 200, sent.text
    assert sent.json()["event_id"]

    case = await client.post("/api/test-cases", json={"name": "Console JSON smoke", "endpoint_id": endpoint.json()["id"], "input_mode": "json", "body_json": {"hello": "case"}})
    assert case.status_code == 200
    run = await client.post(f"/api/test-cases/{case.json()['id']}/run")
    assert run.status_code == 200
    assert run.json()["event_id"]

    invalid_workflow = await client.post("/api/workflows", json={"name": "Invalid lookup workflow", "event_type": "InvalidLookup", "steps_json": [{"name": "receive"}, {"name": "odata_lookup", "config": {"template": "Missing Lookup", "input": {}}}], "validation_json": {"required_fields": []}})
    assert invalid_workflow.status_code == 200
    validation = await client.post(f"/api/workflows/{invalid_workflow.json()['id']}/validate")
    assert validation.status_code == 200
    assert validation.json()["valid"] is False
    assert "Lookup template not found" in validation.json()["errors"][0]["message"]
