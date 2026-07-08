import httpx
import pytest

from app.integration_master.service import render_1c_object_resource


ORDER_GUID = "c3335ee4-43d0-11f1-8388-000c29b755c7"
PRODUCT_GUID = "ff22288c-2da4-11f1-8388-000c29b755c7"
PRODUCT_GUID_2 = "aa22288c-2da4-11f1-8388-000c29b755c7"


async def _create_master_contract(client):
    parse_response = await client.post(
        "/api/integration-master/input/parse",
        json={
            "input_mode": "json",
            "scenario_key": "dnp_chz_code_pool",
            "sample": {
                "operation": "dnp_sinc_pull_codes",
                "sinc": "dnp_sinc_pull_codes",
                "order_name": "26-0666/6938",
                "Number": "260666/6938",
            },
        },
    )
    assert parse_response.status_code == 200, parse_response.text
    parse_result = parse_response.json()
    contract = {
        "name": "DnP запрашивает пул кодов Честного знака",
        "slug": "dnp_sinc_pull_codes",
        "input_mode": "json",
        "source_system": "dnp",
        "scenario_key": "dnp_chz_code_pool",
        "sample": parse_result["normalized_sample"],
        "fields": parse_result["fields"],
        "operation_key": {"type": "field", "field_path": "request.body.sinc", "value": "dnp_sinc_pull_codes", "fallback_paths": ["request.body.operation"]},
        "business_key": {"path": "request.body.order_name"},
    }
    return contract, parse_result


async def _create_mock_odata_connector(client):
    response = await client.post(
        "/api/connectors",
        json={
            "name": "1C CHZ OData ERP",
            "connector_type": "onec",
            "direction": "bidirectional",
            "config_json": {
                "base_url": "http://mock-1c.local/odata/standard.odata",
                "auth": {"type": "none"},
                "odata": {"enabled": True},
                "mock_odata": {
                    "Document_ЗаказНаПроизводство2_2": [
                        {"Ref_Key": ORDER_GUID, "Number": "260666/6938", "Date": "2026-04-29T16:38:53", "Posted": True},
                        {"Ref_Key": "other-order", "Number": "260666/0000", "Date": "2026-04-30T08:00:00", "Posted": True},
                    ],
                    f"Document_ЗаказНаПроизводство2_2(guid'{ORDER_GUID}')/Продукция": [
                        {"Номенклатура_Key": PRODUCT_GUID, "Количество": 180, "КоличествоУпаковок": 180},
                    ],
                    "InformationRegister_ПулКодовМаркировкиСУЗ": [
                        {"Номенклатура_Key": PRODUCT_GUID, "ДокументОснование": ORDER_GUID, "КодМаркировки": "code-001", "Статус": "available"},
                        {"Номенклатура_Key": PRODUCT_GUID, "ДокументОснование": ORDER_GUID, "КодМаркировки": "code-002", "Статус": "available"},
                        {"Номенклатура_Key": PRODUCT_GUID_2, "ДокументОснование": ORDER_GUID, "КодМаркировки": "code-101", "Статус": "available"},
                    ],
                },
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _order_step(connector_id, **overrides):
    step = {
        "connection_id": connector_id,
        "resource": "Document_ЗаказНаПроизводство2_2",
        "filter_mode": "builder",
        "filter_rule": {"field": "Number", "operator": "eq", "value_type": "variable", "value": "request.body.Number"},
        "select": ["Ref_Key", "Number", "Date", "Posted"],
        "top": 1,
        "orderby": "Date desc",
        "paginate": False,
        "save_as": "order",
        "required": True,
    }
    step.update(overrides)
    return step


def _previous_variables(**overrides):
    variables = {
        "order": {
            "Ref_Key": ORDER_GUID,
            "Number": "260666/6938",
            "Date": "2026-04-29T16:38:53",
            "Posted": True,
        }
    }
    variables.update(overrides)
    return variables


def _previous_variables_with_products(products=None, **overrides):
    variables = _previous_variables(
        products=products
        or [
            {
                "Номенклатура_Key": PRODUCT_GUID,
                "Количество": 180,
                "КоличествоУпаковок": 180,
            }
        ]
    )
    variables.update(overrides)
    return variables


def _object_step(connector_id, **overrides):
    step = {
        "connection_id": connector_id,
        "object_variable": "order",
        "key_field": "Ref_Key",
        "key_type": "guid",
        "base_resource": "Document_ЗаказНаПроизводство2_2",
        "nested_resource": "Продукция",
        "select": ["Номенклатура_Key", "Количество", "КоличествоУпаковок"],
        "top": 100,
        "paginate": False,
        "save_as": "products",
        "required": True,
    }
    step.update(overrides)
    return step


def _foreach_step(connector_id, **overrides):
    step = {
        "connection_id": connector_id,
        "items": "products",
        "item_as": "product",
        "resource": "InformationRegister_ПулКодовМаркировкиСУЗ",
        "filter": "Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')",
        "select": ["КодМаркировки", "Номенклатура_Key", "ДокументОснование", "Статус"],
        "top": 500,
        "paginate": True,
        "merge": "flatten",
        "save_as": "codes",
        "required": True,
        "limits": {"max_items": 100, "max_requests": 100, "max_result_rows": 10000},
        "test_limit": 1,
    }
    step.update(overrides)
    return step


def _payload_variables(codes=None, **overrides):
    variables = _previous_variables_with_products()
    variables.update(
        {
            "request": {
                "body": {
                    "operation": "dnp_sinc_pull_codes",
                    "sinc": "dnp_sinc_pull_codes",
                    "order_id": 10271,
                    "order_name": "26-0666/6938",
                    "Number": "260666/6938",
                }
            },
            "codes": codes
            or [
                {"КодМаркировки": "code-001", "Номенклатура_Key": PRODUCT_GUID, "ДокументОснование": ORDER_GUID, "GTIN": "04601234567890"},
                {"КодМаркировки": "code-002", "Номенклатура_Key": PRODUCT_GUID, "ДокументОснование": ORDER_GUID, "GTIN": "04601234567890"},
            ],
            "context": {"run_id": "run-001", "event_id": "evt-001"},
        }
    )
    variables.update(overrides)
    return variables


def _payload_step(**overrides):
    step = {
        "id": "build_dnp_payload",
        "type": "build_payload",
        "body_type": "json",
        "save_as": "target_payload",
        "json_mode": "raw_template",
        "template": {
            "omh": {
                "run_id": "{{context.run_id}}",
                "event_id": "{{context.event_id}}",
                "entity_id": "{{request.body.order_name}}",
                "event_type": "ChestniyZnakCodesSyncRequested",
                "entity_type": "DnPOrder",
                "source_system": "Open Manufacturing Hub",
                "target_system": "DnP",
                "correlation_id": "dnp-chz-sync:{{request.body.order_name}}",
            },
            "payload": {
                "rows": "{{codes}}",
                "order": "{{order}}",
                "order_id": "{{request.body.order_id}}",
                "order_name": "{{request.body.order_name}}",
                "codes_count": "{{codes.length}}",
                "first_gtin": "{{codes[0].GTIN}}",
                "onec_order_number": "{{order.Number}}",
                "order_numbers_by_basis": {"{{order.Ref_Key}}": "{{order.Number}}"},
            },
        },
    }
    step.update(overrides)
    return step


def _final_action_variables(**overrides):
    variables = _payload_variables(context={"run_id": "run-001", "event_id": "evt-001", "queue_item_id": "queue-001"})
    variables["target_payload"] = {
        "omh": {
            "run_id": "run-001",
            "event_id": "evt-001",
            "entity_id": "26-0666/6938",
            "event_type": "ChestniyZnakCodesSyncRequested",
        },
        "payload": {
            "rows": variables["codes"],
            "order_id": 10271,
            "order_name": "26-0666/6938",
            "codes_count": len(variables["codes"]),
        },
    }
    variables.update(overrides)
    return variables


def _final_endpoint_action(**overrides):
    action = {
        "type": "send_endpoint",
        "method": "POST",
        "url": "https://dnp.example.local/api/codes/import",
        "headers": {"Content-Type": "application/json"},
        "body_type": "json",
        "body_source": "target_payload",
        "timeout_seconds": 30,
        "return_to_caller": {"type": "fixed_success", "body": {"ok": True}, "status_code": 200, "headers": {}},
    }
    action.update(overrides)
    return action


async def test_integration_master_scenarios_include_dnp(client):
    response = await client.get("/api/integration-master/scenarios")
    assert response.status_code == 200, response.text
    scenarios = response.json()
    dnp = next(item for item in scenarios if item["key"] == "dnp_chz_code_pool")
    assert dnp["title"] == "Синхронизация пула кодов Честного знака"
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


async def test_save_draft_generates_unique_slug(client):
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
    first = await client.post("/api/integration-master/input/save-draft", json={"contract": contract, "parse_result": parse_result})
    second = await client.post("/api/integration-master/input/save-draft", json={"contract": contract, "parse_result": parse_result})
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["draft"]["slug"] == "lookup_contractor"
    assert second.json()["draft"]["slug"] == "lookup_contractor-2"
    assert second.json()["draft"]["contract"]["endpoint_url"] == "/api/bus/in/lookup_contractor-2"


async def test_odata_step_preview_renders_filter_and_url(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)

    response = await client.post(
        "/api/integration-master/odata-step/preview",
        json={"input_contract": contract, "sample_input": contract["sample"], "odata_step": _order_step(connector["id"])},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["template_filter"] == "Number eq '{{request.body.Number}}'"
    assert body["rendered_filter"] == "Number eq '260666/6938'"
    assert body["rendered_url"] == "Document_ЗаказНаПроизводство2_2?$filter=Number eq '260666/6938'&$select=Ref_Key,Number,Date,Posted&$top=1&$orderby=Date desc"
    assert "order.Ref_Key" in body["variables_after_step"]


async def test_odata_step_validate_reports_top_and_missing_variable(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)

    top_response = await client.post(
        "/api/integration-master/odata-step/validate",
        json={"input_contract": contract, "sample_input": contract["sample"], "odata_step": _order_step(connector["id"], top=501)},
    )
    assert top_response.status_code == 200, top_response.text
    assert top_response.json()["valid"] is False
    assert "$top" in "; ".join(top_response.json()["errors"])

    missing_response = await client.post(
        "/api/integration-master/odata-step/validate",
        json={"input_contract": contract, "sample_input": contract["sample"], "odata_step": _order_step(connector["id"], filter_mode="raw", filter="Number eq '{{request.body.Missing}}'")},
    )
    assert missing_response.status_code == 200, missing_response.text
    assert missing_response.json()["valid"] is False
    assert "Переменная request.body.Missing" in "; ".join(missing_response.json()["errors"])


async def test_odata_step_test_uses_selected_connection_and_maps_result(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)

    response = await client.post(
        "/api/integration-master/odata-step/test",
        json={"input_contract": contract, "sample_input": contract["sample"], "odata_step": _order_step(connector["id"])},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["items_count"] == 1
    assert body["result_preview"]["Ref_Key"] == ORDER_GUID
    assert body["request"]["resource"] == "Document_ЗаказНаПроизводство2_2"
    assert body["request"]["params"]["$filter"] == "Number eq '260666/6938'"
    assert body["request"]["params"]["$select"] == "Ref_Key,Number,Date,Posted"
    assert "order.Ref_Key" in body["variables_after_step"]


async def test_odata_step_test_returns_empty_required_result(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)
    empty_step = _order_step(connector["id"], filter_mode="raw", filter="Number eq 'missing-order'")

    response = await client.post(
        "/api/integration-master/odata-step/test",
        json={"input_contract": contract, "sample_input": contract["sample"], "odata_step": empty_step},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == "ODATA_RESULT_EMPTY"
    assert body["items_count"] == 0


async def test_append_odata_step_to_master_draft(client):
    contract, parse_result = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)
    saved = await client.post("/api/integration-master/input/save-draft", json={"contract": contract, "parse_result": parse_result})
    assert saved.status_code == 200, saved.text
    draft_id = saved.json()["draft"]["id"]

    response = await client.post(
        f"/api/integration-master/drafts/{draft_id}/odata-steps",
        json={"input_contract": contract, "odata_step": _order_step(connector["id"])},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["saved_step"]["id"] == "find_order"
    assert body["saved_step"]["filter"] == "Number eq '{{request.body.Number}}'"
    assert body["saved_step"]["connection_name"] == "1C CHZ OData ERP"
    assert body["draft"]["odata_steps"][0]["save_as"] == "order"
    assert body["draft"]["odata_steps"][0]["resource"] == "Document_ЗаказНаПроизводство2_2"

    loaded = await client.get(f"/api/integration-master/drafts/{draft_id}")
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["odata_steps"][0]["select"] == ["Ref_Key", "Number", "Date", "Posted"]

    saved_again = await client.post(
        f"/api/integration-master/drafts/{draft_id}/odata-steps",
        json={"input_contract": contract, "odata_step": _order_step(connector["id"])},
    )
    assert saved_again.status_code == 200, saved_again.text
    assert len(saved_again.json()["draft"]["odata_steps"]) == 1


def test_render_1c_object_resource_guid_template_and_variables():
    rendered = render_1c_object_resource(
        "Document_ЗаказНаПроизводство2_2",
        "{{order.Ref_Key}}",
        "guid",
        "Продукция",
        _previous_variables(),
    )
    assert rendered.template_resource == "Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция"
    assert rendered.rendered_resource == f"Document_ЗаказНаПроизводство2_2(guid'{ORDER_GUID}')/Продукция"


async def test_odata_object_step_preview_renders_template_and_url(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)

    response = await client.post(
        "/api/integration-master/odata-object-step/preview",
        json={"input_contract": contract, "previous_variables": _previous_variables(), "odata_object_step": _object_step(connector["id"])},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["template_resource"] == "Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция"
    assert body["rendered_resource"] == f"Document_ЗаказНаПроизводство2_2(guid'{ORDER_GUID}')/Продукция"
    assert body["rendered_url"] == f"Document_ЗаказНаПроизводство2_2(guid'{ORDER_GUID}')/Продукция?$select=Номенклатура_Key,Количество,КоличествоУпаковок&$top=100"
    assert body["key_preview"] == ORDER_GUID
    assert "products[0].Номенклатура_Key" in body["variables_after_step"]


async def test_odata_object_step_validate_friendly_errors(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)

    missing_object = await client.post(
        "/api/integration-master/odata-object-step/validate",
        json={"input_contract": contract, "previous_variables": {}, "odata_object_step": _object_step(connector["id"], object_variable="")},
    )
    assert missing_object.status_code == 200, missing_object.text
    assert missing_object.json()["valid"] is False
    assert "Выберите объект" in "; ".join(missing_object.json()["errors"])

    array_object = await client.post(
        "/api/integration-master/odata-object-step/validate",
        json={"input_contract": contract, "previous_variables": {"products": []}, "odata_object_step": _object_step(connector["id"], object_variable="products")},
    )
    assert array_object.status_code == 200, array_object.text
    assert array_object.json()["valid"] is False
    assert "является массивом" in "; ".join(array_object.json()["errors"])

    missing_ref = await client.post(
        "/api/integration-master/odata-object-step/validate",
        json={"input_contract": contract, "previous_variables": {"order": {"Number": "260666/6938"}}, "odata_object_step": _object_step(connector["id"])},
    )
    assert missing_ref.status_code == 200, missing_ref.text
    assert missing_ref.json()["valid"] is False
    assert "нет поля Ref_Key" in "; ".join(missing_ref.json()["errors"])

    invalid_guid = await client.post(
        "/api/integration-master/odata-object-step/validate",
        json={"input_contract": contract, "previous_variables": {"order": {"Ref_Key": "not-a-guid"}}, "odata_object_step": _object_step(connector["id"])},
    )
    assert invalid_guid.status_code == 200, invalid_guid.text
    assert invalid_guid.json()["valid"] is False
    assert "не похоже на GUID" in "; ".join(invalid_guid.json()["errors"])

    invalid_top = await client.post(
        "/api/integration-master/odata-object-step/validate",
        json={"input_contract": contract, "previous_variables": _previous_variables(), "odata_object_step": _object_step(connector["id"], top=501)},
    )
    assert invalid_top.status_code == 200, invalid_top.text
    assert invalid_top.json()["valid"] is False
    assert "$top" in "; ".join(invalid_top.json()["errors"])


async def test_odata_object_step_test_reads_tabular_part(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)

    response = await client.post(
        "/api/integration-master/odata-object-step/test",
        json={"input_contract": contract, "previous_variables": _previous_variables(), "odata_object_step": _object_step(connector["id"])},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["items_count"] == 1
    assert body["rendered_resource"] == f"Document_ЗаказНаПроизводство2_2(guid'{ORDER_GUID}')/Продукция"
    assert body["result_preview"][0]["Номенклатура_Key"] == PRODUCT_GUID
    assert body["request"]["resource"] == f"Document_ЗаказНаПроизводство2_2(guid'{ORDER_GUID}')/Продукция"
    assert body["request"]["params"]["$select"] == "Номенклатура_Key,Количество,КоличествоУпаковок"
    assert "products[]" in body["variables_after_step"]
    assert "products[0].Количество" in body["variables_after_step"]


async def test_odata_object_step_test_returns_empty_required_result(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)

    response = await client.post(
        "/api/integration-master/odata-object-step/test",
        json={"input_contract": contract, "previous_variables": _previous_variables(), "odata_object_step": _object_step(connector["id"], nested_resource="Материалы")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == "ODATA_TABULAR_PART_EMPTY"
    assert body["items_count"] == 0
    assert "Материалы" in body["message"]


async def test_append_odata_object_step_to_master_draft(client):
    contract, parse_result = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)
    saved = await client.post("/api/integration-master/input/save-draft", json={"contract": contract, "parse_result": parse_result})
    assert saved.status_code == 200, saved.text
    draft_id = saved.json()["draft"]["id"]

    first_step = await client.post(
        f"/api/integration-master/drafts/{draft_id}/odata-steps",
        json={"input_contract": contract, "odata_step": _order_step(connector["id"])},
    )
    assert first_step.status_code == 200, first_step.text

    response = await client.post(
        f"/api/integration-master/drafts/{draft_id}/odata-object-steps",
        json={"input_contract": contract, "previous_variables": _previous_variables(), "odata_object_step": _object_step(connector["id"])},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["saved_step"]["id"] == "read_products"
    assert body["saved_step"]["type"] == "odata_object_query"
    assert body["saved_step"]["resource_template"] == "Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция"
    assert body["saved_step"]["connection_name"] == "1C CHZ OData ERP"
    assert body["draft"]["odata_steps"][0]["type"] == "odata_query"
    assert body["draft"]["odata_steps"][1]["type"] == "odata_object_query"
    assert body["draft"]["odata_steps"][1]["save_as"] == "products"

    loaded = await client.get(f"/api/integration-master/drafts/{draft_id}")
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["odata_steps"][1]["nested_resource"] == "Продукция"

    saved_again = await client.post(
        f"/api/integration-master/drafts/{draft_id}/odata-object-steps",
        json={"input_contract": contract, "previous_variables": _previous_variables(), "odata_object_step": _object_step(connector["id"])},
    )
    assert saved_again.status_code == 200, saved_again.text
    assert len(saved_again.json()["draft"]["odata_steps"]) == 2


async def test_foreach_odata_step_preview_renders_first_item_filter_and_url(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)

    response = await client.post(
        "/api/integration-master/foreach-odata-step/preview",
        json={"input_contract": contract, "previous_variables": _previous_variables_with_products(), "foreach_step": _foreach_step(connector["id"])},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["source_count"] == 1
    assert body["first_item_preview"]["Номенклатура_Key"] == PRODUCT_GUID
    assert body["template_filter"] == "Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')"
    assert body["rendered_filter"] == f"Номенклатура_Key eq guid'{PRODUCT_GUID}' and ДокументОснование eq cast(guid'{ORDER_GUID}', 'Document_ЗаказНаПроизводство2_2')"
    assert body["rendered_url"] == (
        "InformationRegister_ПулКодовМаркировкиСУЗ"
        f"?$filter=Номенклатура_Key eq guid'{PRODUCT_GUID}' and ДокументОснование eq cast(guid'{ORDER_GUID}', 'Document_ЗаказНаПроизводство2_2')"
        "&$select=КодМаркировки,Номенклатура_Key,ДокументОснование,Статус&$top=500&paginate=true"
    )
    assert "codes[0].КодМаркировки" in body["variables_after_step"]


async def test_foreach_odata_step_test_runs_query_for_each_product_and_flattens(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)

    response = await client.post(
        "/api/integration-master/foreach-odata-step/test",
        json={"input_contract": contract, "previous_variables": _previous_variables_with_products(), "foreach_step": _foreach_step(connector["id"])},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["items_processed"] == 1
    assert body["odata_requests"] == 1
    assert body["rows_found"] == 2
    assert body["result_preview"][0]["КодМаркировки"] == "code-001"
    assert body["requests"][0]["request"]["resource"] == "InformationRegister_ПулКодовМаркировкиСУЗ"
    assert body["requests"][0]["request"]["params"]["$filter"] == f"Номенклатура_Key eq guid'{PRODUCT_GUID}' and ДокументОснование eq cast(guid'{ORDER_GUID}', 'Document_ЗаказНаПроизводство2_2')"
    assert "codes[0].КодМаркировки" in body["variables_after_step"]


async def test_foreach_odata_step_test_can_process_multiple_products(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)
    products = [
        {"Номенклатура_Key": PRODUCT_GUID, "Количество": 180, "КоличествоУпаковок": 180},
        {"Номенклатура_Key": PRODUCT_GUID_2, "Количество": 1, "КоличествоУпаковок": 1},
    ]

    response = await client.post(
        "/api/integration-master/foreach-odata-step/test",
        json={"input_contract": contract, "previous_variables": _previous_variables_with_products(products=products), "foreach_step": _foreach_step(connector["id"], test_limit=None)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["items_processed"] == 2
    assert body["odata_requests"] == 2
    assert body["rows_found"] == 3
    assert [row["КодМаркировки"] for row in body["result_body"]] == ["code-001", "code-002", "code-101"]
    assert [row["КодМаркировки"] for row in body["result_preview"]] == ["code-001", "code-002", "code-101"]


async def test_foreach_odata_step_merge_modes(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)
    products = [
        {"Номенклатура_Key": PRODUCT_GUID, "Количество": 180, "КоличествоУпаковок": 180},
        {"Номенклатура_Key": PRODUCT_GUID_2, "Количество": 1, "КоличествоУпаковок": 1},
    ]

    grouped = await client.post(
        "/api/integration-master/foreach-odata-step/test",
        json={"input_contract": contract, "previous_variables": _previous_variables_with_products(products=products), "foreach_step": _foreach_step(connector["id"], merge="group_by_item", test_limit=None)},
    )
    assert grouped.status_code == 200, grouped.text
    grouped_body = grouped.json()
    assert grouped_body["success"] is True
    assert grouped_body["result_preview"][0]["item_index"] == 0
    assert len(grouped_body["result_preview"][0]["rows"]) == 2

    first_per_item = await client.post(
        "/api/integration-master/foreach-odata-step/test",
        json={"input_contract": contract, "previous_variables": _previous_variables_with_products(products=products), "foreach_step": _foreach_step(connector["id"], merge="first_per_item", test_limit=None)},
    )
    assert first_per_item.status_code == 200, first_per_item.text
    first_body = first_per_item.json()
    assert first_body["success"] is True
    assert [row["КодМаркировки"] for row in first_body["result_preview"]] == ["code-001", "code-101"]


async def test_foreach_odata_step_validate_friendly_errors(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)

    not_array = await client.post(
        "/api/integration-master/foreach-odata-step/validate",
        json={"input_contract": contract, "previous_variables": _previous_variables(), "foreach_step": _foreach_step(connector["id"], items="order")},
    )
    assert not_array.status_code == 200, not_array.text
    assert not_array.json()["valid"] is False
    assert "не массивом" in "; ".join(not_array.json()["errors"])

    missing_item_field = await client.post(
        "/api/integration-master/foreach-odata-step/validate",
        json={"input_contract": contract, "previous_variables": _previous_variables_with_products(products=[{"Количество": 180}]), "foreach_step": _foreach_step(connector["id"])},
    )
    assert missing_item_field.status_code == 200, missing_item_field.text
    assert missing_item_field.json()["valid"] is False
    assert "product.Номенклатура_Key" in "; ".join(missing_item_field.json()["errors"])

    invalid_top = await client.post(
        "/api/integration-master/foreach-odata-step/validate",
        json={"input_contract": contract, "previous_variables": _previous_variables_with_products(), "foreach_step": _foreach_step(connector["id"], top=501)},
    )
    assert invalid_top.status_code == 200, invalid_top.text
    assert invalid_top.json()["valid"] is False
    assert "$top не может быть больше 500" in "; ".join(invalid_top.json()["errors"])

    request_limit = await client.post(
        "/api/integration-master/foreach-odata-step/validate",
        json={
            "input_contract": contract,
            "previous_variables": _previous_variables_with_products(
                products=[
                    {"Номенклатура_Key": PRODUCT_GUID},
                    {"Номенклатура_Key": PRODUCT_GUID_2},
                ]
            ),
            "foreach_step": _foreach_step(connector["id"], limits={"max_items": 100, "max_requests": 1, "max_result_rows": 10000}),
        },
    )
    assert request_limit.status_code == 200, request_limit.text
    assert request_limit.json()["valid"] is False
    assert "max_requests=1" in "; ".join(request_limit.json()["errors"])


async def test_foreach_odata_step_test_returns_empty_required_result(client):
    contract, _ = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)

    response = await client.post(
        "/api/integration-master/foreach-odata-step/test",
        json={"input_contract": contract, "previous_variables": _previous_variables_with_products(products=[{"Номенклатура_Key": "00000000-0000-0000-0000-000000000000"}]), "foreach_step": _foreach_step(connector["id"])},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == "FOREACH_ODATA_RESULT_EMPTY"
    assert body["rows_found"] == 0


async def test_append_foreach_odata_step_to_master_draft(client):
    contract, parse_result = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)
    saved = await client.post("/api/integration-master/input/save-draft", json={"contract": contract, "parse_result": parse_result})
    assert saved.status_code == 200, saved.text
    draft_id = saved.json()["draft"]["id"]

    first_step = await client.post(
        f"/api/integration-master/drafts/{draft_id}/odata-steps",
        json={"input_contract": contract, "odata_step": _order_step(connector["id"])},
    )
    assert first_step.status_code == 200, first_step.text

    second_step = await client.post(
        f"/api/integration-master/drafts/{draft_id}/odata-object-steps",
        json={"input_contract": contract, "previous_variables": _previous_variables(), "odata_object_step": _object_step(connector["id"])},
    )
    assert second_step.status_code == 200, second_step.text

    response = await client.post(
        f"/api/integration-master/drafts/{draft_id}/foreach-odata-steps",
        json={"input_contract": contract, "previous_variables": _previous_variables_with_products(), "foreach_step": _foreach_step(connector["id"])},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["saved_step"]["id"] == "find_codes"
    assert body["saved_step"]["type"] == "foreach_odata"
    assert body["saved_step"]["connection_name"] == "1C CHZ OData ERP"
    assert body["saved_step"]["items"] == "products"
    assert body["saved_step"]["item_as"] == "product"
    assert body["draft"]["odata_steps"][0]["type"] == "odata_query"
    assert body["draft"]["odata_steps"][1]["type"] == "odata_object_query"
    assert body["draft"]["odata_steps"][2]["type"] == "foreach_odata"

    loaded = await client.get(f"/api/integration-master/drafts/{draft_id}")
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["odata_steps"][2]["save_as"] == "codes"

    saved_again = await client.post(
        f"/api/integration-master/drafts/{draft_id}/foreach-odata-steps",
        json={"input_contract": contract, "previous_variables": _previous_variables_with_products(), "foreach_step": _foreach_step(connector["id"])},
    )
    assert saved_again.status_code == 200, saved_again.text
    assert len(saved_again.json()["draft"]["odata_steps"]) == 3


async def test_payload_step_preview_renders_dnp_json_with_type_preserving_placeholders(client):
    contract, _ = await _create_master_contract(client)

    response = await client.post(
        "/api/integration-master/payload/preview",
        json={"input_contract": contract, "previous_variables": _payload_variables(), "payload_step": _payload_step()},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    rendered = body["rendered_preview"]
    assert body["rendered_body"] == rendered
    assert rendered["omh"]["run_id"] == "run-001"
    assert rendered["omh"]["correlation_id"] == "dnp-chz-sync:26-0666/6938"
    assert isinstance(rendered["payload"]["rows"], list)
    assert rendered["payload"]["rows"][0]["КодМаркировки"] == "code-001"
    assert isinstance(rendered["payload"]["order"], dict)
    assert rendered["payload"]["order"]["Ref_Key"] == ORDER_GUID
    assert rendered["payload"]["order_id"] == 10271
    assert rendered["payload"]["codes_count"] == 2
    assert rendered["payload"]["first_gtin"] == "04601234567890"
    assert rendered["payload"]["order_numbers_by_basis"] == {ORDER_GUID: "260666/6938"}
    assert body["variables_after_step"] == ["target_payload"]


async def test_payload_step_preview_keeps_full_rendered_body_when_preview_is_truncated(client):
    contract, _ = await _create_master_contract(client)
    codes = [
        {"КодМаркировки": f"code-{index:03}", "Номенклатура_Key": PRODUCT_GUID, "ДокументОснование": ORDER_GUID}
        for index in range(1, 6)
    ]

    response = await client.post(
        "/api/integration-master/payload/preview",
        json={"input_contract": contract, "previous_variables": _payload_variables(codes=codes), "payload_step": _payload_step()},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert len(body["rendered_body"]["payload"]["rows"]) == 5
    assert len(body["rendered_preview"]["payload"]["rows"]) == 4
    assert body["rendered_preview"]["payload"]["rows"][-1] == {"_preview_truncated": 2}


async def test_payload_step_json_table_builder_supports_dynamic_object_entries(client):
    contract, _ = await _create_master_contract(client)
    step = _payload_step(
        json_mode="table",
        template=None,
        fields=[
            {"target_path": "omh.run_id", "value_source": "context.run_id", "value_type": "variable"},
            {"target_path": "omh.event_type", "value_source": "ChestniyZnakCodesSyncRequested", "value_type": "constant_string"},
            {"target_path": "omh.correlation_id", "value_source": "dnp-chz-sync:{{request.body.order_name}}", "value_type": "template_string"},
            {"target_path": "payload.rows", "value_source": "codes", "value_type": "array"},
            {"target_path": "payload.order_id", "value_source": "request.body.order_id", "value_type": "variable"},
            {"target_path": "payload.onec_order_number", "value_source": "order.Number", "value_type": "variable"},
        ],
        dynamic_entries=[
            {"object_path": "payload.order_numbers_by_basis", "key_source": "order.Ref_Key", "value_source": "order.Number", "value_type": "variable"},
        ],
    )

    response = await client.post(
        "/api/integration-master/payload/preview",
        json={"input_contract": contract, "previous_variables": _payload_variables(), "payload_step": step},
    )
    assert response.status_code == 200, response.text
    rendered = response.json()["rendered_preview"]
    assert rendered["payload"]["rows"][1]["КодМаркировки"] == "code-002"
    assert rendered["payload"]["order_numbers_by_basis"][ORDER_GUID] == "260666/6938"
    assert rendered["omh"]["correlation_id"] == "dnp-chz-sync:26-0666/6938"


async def test_payload_step_raw_json_template_string_is_validated_before_render(client):
    contract, _ = await _create_master_contract(client)

    invalid = await client.post(
        "/api/integration-master/payload/validate",
        json={"input_contract": contract, "previous_variables": _payload_variables(), "payload_step": _payload_step(template='{"payload": ')},
    )
    assert invalid.status_code == 200, invalid.text
    assert invalid.json()["valid"] is False
    assert invalid.json()["error_code"] == "PAYLOAD_JSON_INVALID"
    assert "JSON template" in "; ".join(invalid.json()["errors"])

    valid = await client.post(
        "/api/integration-master/payload/preview",
        json={"input_contract": contract, "previous_variables": _payload_variables(), "payload_step": _payload_step(template='{"rows":"{{codes}}","keyed":{"{{order.Ref_Key}}":"{{order.Number}}"}}')},
    )
    assert valid.status_code == 200, valid.text
    rendered = valid.json()["rendered_preview"]
    assert rendered["rows"][0]["КодМаркировки"] == "code-001"
    assert rendered["keyed"][ORDER_GUID] == "260666/6938"


async def test_payload_step_missing_variable_returns_friendly_error_code(client):
    contract, _ = await _create_master_contract(client)

    response = await client.post(
        "/api/integration-master/payload/preview",
        json={"input_contract": contract, "previous_variables": _payload_variables(), "payload_step": _payload_step(template={"payload": {"basis": "{{order.Missing}}"}})},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert body["error_code"] == "VARIABLE_NOT_FOUND"
    assert body["errors"] == ["Переменная order.Missing не найдена."]


async def test_payload_step_xml_and_raw_text_render(client):
    contract, _ = await _create_master_contract(client)

    xml_response = await client.post(
        "/api/integration-master/payload/preview",
        json={
            "input_contract": contract,
            "previous_variables": _payload_variables(order={"Ref_Key": ORDER_GUID, "Number": "260666&6938"}),
            "payload_step": {
                "type": "build_payload",
                "body_type": "xml",
                "save_as": "target_payload",
                "template": "<Response><RowsCount>{{codes.length}}</RowsCount><Order>{{order.Number}}</Order></Response>",
            },
        },
    )
    assert xml_response.status_code == 200, xml_response.text
    assert xml_response.json()["valid"] is True
    assert xml_response.json()["rendered_preview"] == "<Response><RowsCount>2</RowsCount><Order>260666&amp;6938</Order></Response>"

    raw_response = await client.post(
        "/api/integration-master/payload/preview",
        json={
            "input_contract": contract,
            "previous_variables": _payload_variables(),
            "payload_step": {
                "type": "build_payload",
                "body_type": "raw_text",
                "save_as": "target_payload",
                "template": "OK order={{order.Number}} codes={{codes.length}}",
            },
        },
    )
    assert raw_response.status_code == 200, raw_response.text
    assert raw_response.json()["rendered_preview"] == "OK order=260666/6938 codes=2"


async def test_append_payload_step_to_master_draft(client):
    contract, parse_result = await _create_master_contract(client)
    connector = await _create_mock_odata_connector(client)
    saved = await client.post("/api/integration-master/input/save-draft", json={"contract": contract, "parse_result": parse_result})
    assert saved.status_code == 200, saved.text
    draft_id = saved.json()["draft"]["id"]

    first_step = await client.post(
        f"/api/integration-master/drafts/{draft_id}/odata-steps",
        json={"input_contract": contract, "odata_step": _order_step(connector["id"])},
    )
    assert first_step.status_code == 200, first_step.text

    second_step = await client.post(
        f"/api/integration-master/drafts/{draft_id}/odata-object-steps",
        json={"input_contract": contract, "previous_variables": _previous_variables(), "odata_object_step": _object_step(connector["id"])},
    )
    assert second_step.status_code == 200, second_step.text

    third_step = await client.post(
        f"/api/integration-master/drafts/{draft_id}/foreach-odata-steps",
        json={"input_contract": contract, "previous_variables": _previous_variables_with_products(), "foreach_step": _foreach_step(connector["id"])},
    )
    assert third_step.status_code == 200, third_step.text

    response = await client.post(
        f"/api/integration-master/drafts/{draft_id}/payload-steps",
        json={"input_contract": contract, "previous_variables": _payload_variables(), "payload_step": _payload_step()},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["saved_step"]["id"] == "build_dnp_payload"
    assert body["saved_step"]["type"] == "build_payload"
    assert body["saved_step"]["body_type"] == "json"
    assert body["saved_step"]["save_as"] == "target_payload"
    assert body["saved_step"]["last_preview_status"] == "success"
    assert body["draft"]["odata_steps"][3]["type"] == "build_payload"

    loaded = await client.get(f"/api/integration-master/drafts/{draft_id}")
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["odata_steps"][3]["save_as"] == "target_payload"


async def test_final_action_preview_return_json_response(client):
    contract, _ = await _create_master_contract(client)

    response = await client.post(
        "/api/integration-master/final-action/preview",
        json={
            "input_contract": contract,
            "previous_variables": _final_action_variables(),
            "final_action": {
                "type": "return_response",
                "body_type": "json",
                "body_source": "target_payload",
                "return_to_caller": {"type": "fixed_success", "body": {"ok": True}, "status_code": 200, "headers": {"Content-Type": "application/json"}},
            },
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["valid"] is True
    assert body["caller_response_preview"]["payload"]["codes_count"] == 2
    assert body["send_preview"] is None


async def test_final_action_preview_return_xml_custom_response(client):
    contract, _ = await _create_master_contract(client)

    response = await client.post(
        "/api/integration-master/final-action/preview",
        json={
            "input_contract": contract,
            "previous_variables": _final_action_variables(),
            "final_action": {
                "type": "return_response",
                "body_type": "xml",
                "body_source": "custom",
                "custom_body": "<Response><Order>{{request.body.order_name}}</Order><Codes>{{codes.length}}</Codes></Response>",
                "return_to_caller": {"type": "fixed_success", "body": {}, "status_code": 200, "headers": {"Content-Type": "application/xml"}},
            },
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["caller_response_preview"] == "<Response><Order>26-0666/6938</Order><Codes>2</Codes></Response>"


async def test_final_action_preview_send_endpoint_with_target_payload(client):
    contract, _ = await _create_master_contract(client)

    response = await client.post(
        "/api/integration-master/final-action/preview",
        json={"input_contract": contract, "previous_variables": _final_action_variables(), "final_action": _final_endpoint_action()},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["send_preview"]["method"] == "POST"
    assert body["send_preview"]["url"] == "https://dnp.example.local/api/codes/import"
    assert body["send_preview"]["body_preview"]["payload"]["codes_count"] == 2
    assert body["caller_response_preview"] == {"ok": True}


async def test_final_action_dry_run_does_not_call_network(client, monkeypatch):
    contract, _ = await _create_master_contract(client)

    class FailingHttpClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, *args, **kwargs):
            raise AssertionError("dry-run must not call target endpoint")

    monkeypatch.setattr("app.integration_master.final_action.HTTP_CLIENT_CLS", FailingHttpClient)
    response = await client.post(
        "/api/integration-master/final-action/test",
        json={"input_contract": contract, "previous_variables": _final_action_variables(), "final_action": _final_endpoint_action(), "dry_run": True},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["dry_run"] is True
    assert body["would_send"]["url"] == "https://dnp.example.local/api/codes/import"
    assert body["would_return_to_caller"] == {"ok": True}
    assert body["target_status"] is None


async def test_final_action_real_test_can_be_mocked(client, monkeypatch):
    contract, _ = await _create_master_contract(client)
    seen: dict[str, object] = {}

    class FakeHttpClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method, url, headers=None, **kwargs):
            seen["method"] = method
            seen["url"] = url
            seen["headers"] = headers
            seen["json"] = kwargs.get("json")
            return httpx.Response(200, json={"ok": True, "rows_count": 180}, headers={"content-type": "application/json"})

    monkeypatch.setattr("app.integration_master.final_action.HTTP_CLIENT_CLS", FakeHttpClient)
    response = await client.post(
        "/api/integration-master/final-action/test",
        json={"input_contract": contract, "previous_variables": _final_action_variables(), "final_action": _final_endpoint_action(), "dry_run": False},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["dry_run"] is False
    assert body["target_status"] == 200
    assert body["target_response"] == {"ok": True, "rows_count": 180}
    assert body["caller_response"] == {"ok": True}
    assert seen["method"] == "POST"
    assert seen["json"]["payload"]["codes_count"] == 2


async def test_final_action_proxy_response_and_target_error(client, monkeypatch):
    contract, _ = await _create_master_contract(client)

    class ProxyHttpClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method, url, headers=None, **kwargs):
            return httpx.Response(201, json={"accepted": True, "target_id": "dnp-001"}, headers={"content-type": "application/json"})

    monkeypatch.setattr("app.integration_master.final_action.HTTP_CLIENT_CLS", ProxyHttpClient)
    proxy = await client.post(
        "/api/integration-master/final-action/test",
        json={
            "input_contract": contract,
            "previous_variables": _final_action_variables(),
            "final_action": _final_endpoint_action(type="send_and_return_response", return_to_caller={"type": "fixed_success", "body": {"ok": True}, "status_code": 200, "headers": {}}),
            "dry_run": False,
        },
    )
    assert proxy.status_code == 200, proxy.text
    assert proxy.json()["caller_response"] == {"accepted": True, "target_id": "dnp-001"}

    class ErrorHttpClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def request(self, method, url, headers=None, **kwargs):
            return httpx.Response(400, json={"error": "bad payload"}, headers={"content-type": "application/json"})

    monkeypatch.setattr("app.integration_master.final_action.HTTP_CLIENT_CLS", ErrorHttpClient)
    error = await client.post(
        "/api/integration-master/final-action/test",
        json={"input_contract": contract, "previous_variables": _final_action_variables(), "final_action": _final_endpoint_action(), "dry_run": False},
    )
    assert error.status_code == 200, error.text
    assert error.json()["success"] is False
    assert error.json()["error_code"] == "TARGET_ENDPOINT_ERROR"
    assert error.json()["target_response"] == {"error": "bad payload"}


async def test_final_action_accepted_event_preview(client):
    contract, _ = await _create_master_contract(client)

    response = await client.post(
        "/api/integration-master/final-action/preview",
        json={"input_contract": contract, "previous_variables": _final_action_variables(), "final_action": {"type": "accepted_event", "return_to_caller": {"type": "accepted_event", "body": {}, "status_code": 202, "headers": {}}}},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["caller_response_preview"] == {"accepted": True, "event_id": "evt-001", "queue_item_id": "queue-001", "timeline_url": "/events/evt-001"}


async def test_final_action_validate_url_body_and_private_warnings(client):
    contract, _ = await _create_master_contract(client)

    missing_url = await client.post(
        "/api/integration-master/final-action/validate",
        json={"input_contract": contract, "previous_variables": _final_action_variables(), "final_action": _final_endpoint_action(url="")},
    )
    assert missing_url.status_code == 200, missing_url.text
    assert missing_url.json()["valid"] is False
    assert missing_url.json()["error_code"] == "FINAL_ACTION_URL_REQUIRED"

    invalid_url = await client.post(
        "/api/integration-master/final-action/validate",
        json={"input_contract": contract, "previous_variables": _final_action_variables(), "final_action": _final_endpoint_action(url="ftp://example.local/import")},
    )
    assert invalid_url.status_code == 200, invalid_url.text
    assert invalid_url.json()["valid"] is False
    assert invalid_url.json()["error_code"] == "FINAL_ACTION_URL_INVALID"

    private_url = await client.post(
        "/api/integration-master/final-action/validate",
        json={"input_contract": contract, "previous_variables": _final_action_variables(), "final_action": _final_endpoint_action(url="http://172.16.3.10/api/import")},
    )
    assert private_url.status_code == 200, private_url.text
    assert private_url.json()["valid"] is True
    assert "private IP" in "; ".join(private_url.json()["warnings"])

    missing_payload = await client.post(
        "/api/integration-master/final-action/validate",
        json={"input_contract": contract, "previous_variables": _payload_variables(), "final_action": _final_endpoint_action()},
    )
    assert missing_payload.status_code == 200, missing_payload.text
    assert missing_payload.json()["valid"] is False
    assert missing_payload.json()["error_code"] == "FINAL_ACTION_BODY_SOURCE_MISSING"

    form_body = await client.post(
        "/api/integration-master/final-action/validate",
        json={"input_contract": contract, "previous_variables": _final_action_variables(), "final_action": _final_endpoint_action(body_type="form")},
    )
    assert form_body.status_code == 200, form_body.text
    assert form_body.json()["valid"] is False
    assert form_body.json()["error_code"] == "FINAL_ACTION_BODY_TYPE_UNSUPPORTED"


async def test_save_final_action_to_master_draft(client):
    contract, parse_result = await _create_master_contract(client)
    saved = await client.post("/api/integration-master/input/save-draft", json={"contract": contract, "parse_result": parse_result})
    assert saved.status_code == 200, saved.text
    draft_id = saved.json()["draft"]["id"]

    payload_step = await client.post(
        f"/api/integration-master/drafts/{draft_id}/payload-steps",
        json={"input_contract": contract, "previous_variables": _payload_variables(), "payload_step": _payload_step()},
    )
    assert payload_step.status_code == 200, payload_step.text

    response = await client.post(
        f"/api/integration-master/drafts/{draft_id}/final-action",
        json={"input_contract": contract, "previous_variables": _final_action_variables(), "final_action": _final_endpoint_action(url="http://172.16.3.10/api/v2/integrations/omh/chz/codes/import")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["final_action"]["type"] == "send_endpoint"
    assert body["final_action"]["last_test_status"] == "configured"
    assert body["draft"]["final_action"]["url"] == "http://172.16.3.10/api/v2/integrations/omh/chz/codes/import"
    assert body["draft"]["odata_steps"][0]["type"] == "build_payload"

    loaded = await client.get(f"/api/integration-master/drafts/{draft_id}")
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["final_action"]["body_source"] == "target_payload"


async def _create_complete_master_draft(client, *, slug="dnp_sinc_pull_codes", final_action=None):
    contract, parse_result = await _create_master_contract(client)
    contract = {**contract, "slug": slug, "name": f"{contract['name']} {slug}"}
    connector = await _create_mock_odata_connector(client)
    saved = await client.post("/api/integration-master/input/save-draft", json={"contract": contract, "parse_result": parse_result})
    assert saved.status_code == 200, saved.text
    draft_id = saved.json()["draft"]["id"]

    order = await client.post(
        f"/api/integration-master/drafts/{draft_id}/odata-steps",
        json={"input_contract": contract, "odata_step": _order_step(connector["id"])},
    )
    assert order.status_code == 200, order.text

    products = await client.post(
        f"/api/integration-master/drafts/{draft_id}/odata-object-steps",
        json={"input_contract": contract, "previous_variables": _previous_variables(), "odata_object_step": _object_step(connector["id"])},
    )
    assert products.status_code == 200, products.text

    codes = await client.post(
        f"/api/integration-master/drafts/{draft_id}/foreach-odata-steps",
        json={"input_contract": contract, "previous_variables": _previous_variables_with_products(), "foreach_step": _foreach_step(connector["id"])},
    )
    assert codes.status_code == 200, codes.text

    payload = await client.post(
        f"/api/integration-master/drafts/{draft_id}/payload-steps",
        json={"input_contract": contract, "previous_variables": _payload_variables(), "payload_step": _payload_step()},
    )
    assert payload.status_code == 200, payload.text

    final = await client.post(
        f"/api/integration-master/drafts/{draft_id}/final-action",
        json={"input_contract": contract, "previous_variables": _final_action_variables(), "final_action": final_action or _final_endpoint_action(url="http://172.16.3.10/api/v2/integrations/omh/chz/codes/import")},
    )
    assert final.status_code == 200, final.text
    return final.json()["draft"], contract, parse_result


async def test_compile_validation_complete_dnp_draft_success(client):
    draft, _, _ = await _create_complete_master_draft(client, slug="dnp_compile_validate")

    response = await client.post(f"/api/integration-master/drafts/{draft['id']}/validate-for-compile")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["errors"] == []


async def test_compile_validation_missing_final_action_fails(client):
    contract, parse_result = await _create_master_contract(client)
    contract = {**contract, "slug": "dnp_compile_missing_final", "name": "DnP missing final"}
    saved = await client.post("/api/integration-master/input/save-draft", json={"contract": contract, "parse_result": parse_result})
    assert saved.status_code == 200, saved.text

    response = await client.post(f"/api/integration-master/drafts/{saved.json()['draft']['id']}/validate-for-compile")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert any(item["section"] == "final_action" for item in body["errors"])


async def test_compile_preview_returns_objects_and_builder_json(client):
    draft, _, _ = await _create_complete_master_draft(client, slug="dnp_compile_preview")

    response = await client.post(f"/api/integration-master/drafts/{draft['id']}/compile-preview")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["will_create"]["integration_endpoint"]["url"] == "/api/bus/in/dnp_compile_preview"
    assert body["will_create"]["integration_flow"]["steps_count"] >= 5
    step_types = [step["type"] for step in body["advanced"]["builder_json"]["steps"]]
    assert "build_payload" in step_types
    assert "call_endpoint" in step_types
    assert body["advanced"]["builder_json"]["source"]["master_steps"][1]["type"] == "odata_object_query"


async def test_compile_creates_disabled_flow_endpoint_route_test_case_and_audit(client):
    draft, _, _ = await _create_complete_master_draft(client, slug="dnp_compile_create")

    response = await client.post(
        f"/api/integration-master/drafts/{draft['id']}/compile",
        json={"enabled": False, "create_saved_test_case": True, "comment": "pytest compile"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["enabled"] is False
    assert body["endpoint"] == {"method": "POST", "url": "/api/bus/in/dnp_compile_create"}
    assert body["endpoint_id"]
    assert body["route_id"]
    assert body["integration_flow_id"]
    assert body["saved_test_case_id"]

    flow = await client.get(f"/api/integration-flows/{body['integration_flow_id']}")
    assert flow.status_code == 200, flow.text
    flow_body = flow.json()
    assert flow_body["enabled"] is False
    assert flow_body["builder_json"]["steps"][3]["type"] == "build_payload"
    assert flow_body["last_validation_json"]["valid"] is True

    test_case = await client.get(f"/api/test-cases/{body['saved_test_case_id']}")
    assert test_case.status_code == 200, test_case.text
    assert test_case.json()["body_json"]["sinc"] == "dnp_sinc_pull_codes"

    dry_run = await client.post(f"/api/integration-master/compiled/{body['integration_flow_id']}/run-test", json={"dry_run": True})
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["success"] is True
    assert dry_run.json()["dry_run"] is True

    enabled = await client.post(f"/api/integration-master/compiled/{body['integration_flow_id']}/enable")
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["enabled"] is True
    assert enabled.json()["endpoint_enabled"] is True
    assert enabled.json()["route_enabled"] is True

    audit = await client.get("/api/audit", params={"action": "integration_master.compiled", "object_id": draft["id"]})
    assert audit.status_code == 200, audit.text
    assert audit.json()["total"] >= 1


async def test_compile_duplicate_slug_conflict_is_transactional(client):
    draft, _, _ = await _create_complete_master_draft(client, slug="dnp_compile_duplicate")
    first = await client.post(f"/api/integration-master/drafts/{draft['id']}/compile", json={"enabled": False, "create_saved_test_case": True})
    assert first.status_code == 200, first.text
    before = await client.get("/api/integration-flows")
    assert before.status_code == 200, before.text
    before_count = len(before.json())

    duplicate = await client.post(f"/api/integration-master/drafts/{draft['id']}/compile", json={"enabled": False, "create_saved_test_case": True})
    assert duplicate.status_code == 400, duplicate.text
    assert "/api/bus/in/dnp_compile_duplicate" in duplicate.text
    after = await client.get("/api/integration-flows")
    assert after.status_code == 200, after.text
    assert len(after.json()) == before_count
