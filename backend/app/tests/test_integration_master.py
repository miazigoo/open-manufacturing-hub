import pytest


async def test_integration_master_scenarios_include_dnp(client):
    response = await client.get("/api/integration-master/scenarios")
    assert response.status_code == 200, response.text
    scenarios = response.json()
    dnp = next(item for item in scenarios if item["key"] == "dnp_chz_code_pool")
    assert dnp["title"] == "DnP запрашивает пул кодов Честного знака"
    assert dnp["default_slug"] == "dnp_sinc_pull_codes"
    assert dnp["sample"]["sinc"] == "dnp_sinc_pull_codes"


async def test_parse_dnp_json_infers_fields_and_keys(client):
    payload = {
        "input_mode": "json",
        "scenario_key": "dnp_chz_code_pool",
        "sample": {
            "operation": "dnp_sinc_pull_codes",
            "sinc": "dnp_sinc_pull_codes",
            "order_id": 10271,
            "order_name": "26-0666/6938",
            "Number": "260666/6938",
        },
    }
    response = await client.post("/api/integration-master/input/parse", json=payload)
    assert response.status_code == 200, response.text
    body = response.json()
    fields = {item["path"]: item for item in body["fields"]}
    assert fields["request.body.operation"]["type"] == "string"
    assert fields["request.body.order_id"]["type"] == "number"
    assert fields["request.body.Number"]["example"] == "260666/6938"
    assert body["suggested_operation_keys"][0]["field_path"] == "request.body.sinc"
    assert body["suggested_operation_keys"][0]["fallback_paths"] == ["request.body.operation"]
    assert body["suggested_operation_keys"][0]["matcher_json"]["rules"][0] == {"type": "body_path_equals", "path": "sinc", "value": "dnp_sinc_pull_codes"}
    assert body["suggested_business_keys"][0]["path"] == "request.body.order_name"


async def test_parse_json_arrays(client):
    response = await client.post(
        "/api/integration-master/input/parse",
        json={
            "input_mode": "json",
            "sample": {"operation": "create_wms_shipment", "items": [{"sku": "ABC-123", "qty": 10}]},
        },
    )
    assert response.status_code == 200, response.text
    fields = {item["path"]: item for item in response.json()["fields"]}
    assert fields["request.body.items[]"]["type"] == "array"
    assert fields["request.body.items[0].sku"]["example"] == "ABC-123"
    assert fields["request.body.items[0].qty"]["type"] == "number"


async def test_parse_xml_paths(client):
    response = await client.post(
        "/api/integration-master/input/parse",
        json={"input_mode": "xml", "sample": "<Документ><Тип>УПД</Тип><Номер>123</Номер><ИНН>7707083893</ИНН></Документ>"},
    )
    assert response.status_code == 200, response.text
    fields = {item["path"]: item for item in response.json()["fields"]}
    assert fields["xml./Документ/Тип"]["display_path"] == "/Документ/Тип"
    assert fields["xml./Документ/Номер"]["example"] == "123"
    assert fields["xml./Документ/ИНН"]["type"] == "number"


async def test_parse_raw_text_contract(client):
    response = await client.post(
        "/api/integration-master/input/parse",
        json={"input_mode": "raw_text", "sample": "operation=dnp_sinc_pull_codes;Number=260666/6938"},
    )
    assert response.status_code == 200, response.text
    fields = {item["path"]: item for item in response.json()["fields"]}
    assert fields["request.raw_text"]["type"] == "string"
    assert fields["request.raw_text.operation"]["example"] == "dnp_sinc_pull_codes"
    assert fields["request.raw_text.Number"]["example"] == "260666/6938"


async def test_parse_invalid_json_returns_clear_error(client):
    response = await client.post("/api/integration-master/input/parse", json={"input_mode": "json", "sample": '{"operation": '})
    assert response.status_code == 400
    assert "JSON не удалось разобрать" in response.json()["detail"]


async def test_validate_endpoint_slug(client):
    valid = await client.post(
        "/api/integration-master/input/validate",
        json={
            "contract": {
                "name": "Lookup contractor",
                "slug": "lookup_contractor",
                "input_mode": "json",
                "source_system": "external_api",
                "sample": {"operation": "lookup_contractor", "inn": "7707083893"},
                "fields": [
                    {"name": "operation", "path": "request.body.operation", "type": "string", "required": True, "example": "lookup_contractor"},
                    {"name": "inn", "path": "request.body.inn", "type": "string", "required": True, "example": "7707083893"},
                ],
                "operation_key": {"type": "field", "field_path": "request.body.operation", "value": "lookup_contractor"},
                "business_key": {"path": "request.body.inn"},
            }
        },
    )
    assert valid.status_code == 200, valid.text
    assert valid.json()["valid"] is True
    assert valid.json()["endpoint_url"] == "/api/bus/in/lookup_contractor"

    invalid = await client.post(
        "/api/integration-master/input/validate",
        json={
            "contract": {
                "name": "Bad",
                "slug": "Bad Slug",
                "input_mode": "json",
                "source_system": "external_api",
                "sample": {"operation": "x"},
                "fields": [{"name": "operation", "path": "request.body.operation", "type": "string", "required": True, "example": "x"}],
            }
        },
    )
    assert invalid.status_code == 200, invalid.text
    assert invalid.json()["valid"] is False
    assert "Endpoint slug" in invalid.json()["errors"][0]


async def test_save_and_load_input_contract_draft(client):
    parse_response = await client.post(
        "/api/integration-master/input/parse",
        json={"input_mode": "json", "scenario_key": "external_contractor_lookup", "sample": {"operation": "lookup_contractor", "inn": "7707083893"}},
    )
    assert parse_response.status_code == 200, parse_response.text
    parse_result = parse_response.json()
    contract = {
        "name": "Внешний сайт запрашивает данные из 1C",
        "slug": "lookup_contractor",
        "input_mode": "json",
        "source_system": "external_api",
        "scenario_key": "external_contractor_lookup",
        "sample": parse_result["normalized_sample"],
        "fields": parse_result["fields"],
        "operation_key": {"type": "field", "field_path": "request.body.operation", "value": "lookup_contractor"},
        "business_key": {"path": "request.body.inn"},
    }
    saved = await client.post("/api/integration-master/input/save-draft", json={"contract": contract, "parse_result": parse_result})
    assert saved.status_code == 200, saved.text
    saved_body = saved.json()
    draft = saved_body["draft"]
    assert draft["endpoint_url"] == "/api/bus/in/lookup_contractor"
    assert saved_body["next_steps"]

    loaded = await client.get(f"/api/integration-master/drafts/{draft['id']}")
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["contract"]["business_key"]["path"] == "request.body.inn"
    assert loaded.json()["parse_result"]["fields"][0]["path"] == "request.body.operation"
