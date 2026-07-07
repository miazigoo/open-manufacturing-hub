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
