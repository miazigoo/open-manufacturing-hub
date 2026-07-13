ORDER_REF = "c3335ee4-43d0-11f1-8388-000c29b755c7"
PRODUCT_REF = "ff22288c-2da4-11f1-8388-000c29b755c7"
CUSTOMER_ORDER_REF = "66666666-6666-6666-6666-666666666666"
CUSTOMER_PRODUCT_REF = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"

DNP_CODE_SELECT = [
    "КодМаркировки",
    "ПолныйКодМаркировки",
    "ХешСуммаКодаМаркировки",
    "Статус",
    "Организация_Key",
    "СтанцияУправленияЗаказами_Key",
    "Номенклатура_Key",
    "Характеристика_Key",
    "ДатаЭмиссииУниверсальная",
    "ДатаПечатиУниверсальная",
    "ШтрихкодУпаковки_Key",
    "GTIN",
    "МаксимальнаяРозничнаяЦена",
    "СпособВводаВОборот",
    "Шаблон",
    "ХешСуммаУпаковки",
    "ТипШтрихкода",
    "МаркировкаОстатков",
    "СрокГодности",
    "ЗаказНаЭмиссию_Key",
    "ИдентификаторЗаказаСУЗ",
    "ИдентификаторБлокаСУЗ",
    "ВидКИЗ",
    "РазмерКИЗ",
    "ДокументОснование",
    "ДокументОснование_Type",
]


async def test_integration_patterns_list_and_get(client):
    response = await client.get("/api/integration-patterns")
    assert response.status_code == 200, response.text
    patterns = response.json()
    assert len(patterns) >= 11
    ids = {item["pattern_id"] for item in patterns}
    assert "request_odata_response" in ids
    assert "request_multiple_odata_response" in ids
    assert "request_save_file_optional_forward" in ids
    assert "request_odata_object_foreach_send_endpoint" in ids
    assert "source_web_api_writeback_onec" in ids
    assert "wms_fact_to_onec" in ids

    detail = await client.get("/api/integration-patterns/request_odata_foreach_send_endpoint")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["recommended_wizard"] == "odata_integration_master"
    assert "foreach_odata" in body["initial_steps"]

    dnp = await client.get("/api/integration-patterns/request_odata_object_foreach_send_endpoint")
    assert dnp.status_code == 200, dnp.text
    assert dnp.json()["wizard_route"] == "/master?pattern=request_odata_object_foreach_send_endpoint"
    assert dnp.json()["docs_link"] == "/docs/onec/recipes/dnp-chz-code-pool-sync"

    writeback = await client.get("/api/integration-patterns/source_web_api_writeback_onec")
    assert writeback.status_code == 200, writeback.text
    assert writeback.json()["status"] == "available"
    assert writeback.json()["wizard_route"] == "/master?pattern=source_web_api_writeback_onec"
    assert writeback.json()["docs_link"] == "/docs/onec/recipes/onec-site-writeback"

    multiple = await client.get("/api/integration-patterns/request_multiple_odata_response")
    assert multiple.status_code == 200, multiple.text
    assert multiple.json()["wizard_route"] == "/master?pattern=request_multiple_odata_response"
    assert multiple.json()["docs_link"] == "/docs/onec/recipes/request-odata-xml-response"

    wms = await client.get("/api/integration-patterns/wms_fact_to_onec")
    assert wms.status_code == 200, wms.text
    assert wms.json()["wizard_route"] == "/master?pattern=wms_fact_to_onec"
    assert wms.json()["docs_link"] == "/docs/onec/recipes/wms-shipment-fact-to-onec"

    xml_raw = await client.get("/api/integration-patterns/xml_raw_bridge")
    assert xml_raw.status_code == 200, xml_raw.text
    assert xml_raw.json()["wizard_route"] == "/master?pattern=xml_raw_bridge"
    assert xml_raw.json()["docs_link"] == "/docs/onec/recipes/xml-raw-forwarding"

    xml_odata = await client.get("/api/integration-patterns/xml_odata_xml_response")
    assert xml_odata.status_code == 200, xml_odata.text
    assert xml_odata.json()["wizard_route"] == "/master?pattern=xml_odata_xml_response"
    assert xml_odata.json()["docs_link"] == "/docs/onec/recipes/xml-input-odata-xml-response"

    request_print = await client.get("/api/integration-patterns/request_print")
    assert request_print.status_code == 200, request_print.text
    assert request_print.json()["wizard_route"] == "/master?pattern=request_print"
    assert request_print.json()["docs_link"] == "/docs/onec/recipes/onec-print-labels"


async def test_integration_patterns_recommend_dnp_like_foreach(client):
    response = await client.post(
        "/api/integration-patterns/recommend",
        json={
            "source_system": "external_api",
            "input_mode": "json",
            "needs_odata": True,
            "needs_foreach": True,
            "needs_file_save": False,
            "needs_response": True,
            "needs_send_endpoint": True,
        },
    )
    assert response.status_code == 200, response.text
    first = response.json()["recommended_patterns"][0]
    assert first["pattern_id"] == "request_odata_object_foreach_send_endpoint"
    assert first["confidence"] >= 0.9
    assert "foreach" in first["reason"]


async def test_integration_patterns_recommend_chz_file_save(client):
    response = await client.post(
        "/api/integration-patterns/recommend",
        json={
            "source_system": "onec",
            "input_mode": "json",
            "needs_file_save": True,
            "needs_send_endpoint": True,
        },
    )
    assert response.status_code == 200, response.text
    first = response.json()["recommended_patterns"][0]
    assert first["pattern_id"] == "request_save_file_optional_forward"
    assert first["pattern"]["wizard_route"] == "/marking-code-pools"


async def test_integration_patterns_start_returns_wizard_route_and_steps(client):
    response = await client.post(
        "/api/integration-patterns/start",
        json={"pattern_id": "request_odata_foreach_send_endpoint"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["wizard_route"] == "/master?pattern=request_odata_foreach_send_endpoint"
    assert body["initial_steps"] == [
        "input_contract",
        "odata_query",
        "odata_object_query",
        "foreach_odata",
        "payload_builder",
        "final_action",
    ]

    chz = await client.post("/api/integration-patterns/start", json={"pattern_id": "request_save_file_optional_forward"})
    assert chz.status_code == 200, chz.text
    assert chz.json()["wizard_route"] == "/marking-code-pools"

    dnp = await client.post("/api/integration-patterns/start", json={"pattern_id": "request_odata_object_foreach_send_endpoint"})
    assert dnp.status_code == 200, dnp.text
    assert dnp.json()["wizard_route"] == "/master?pattern=request_odata_object_foreach_send_endpoint"
    assert dnp.json()["recommended_wizard"] == "dnp_chz_code_pool_wizard"

    writeback = await client.post("/api/integration-patterns/start", json={"pattern_id": "source_web_api_writeback_onec"})
    assert writeback.status_code == 200, writeback.text
    assert writeback.json()["wizard_route"] == "/master?pattern=source_web_api_writeback_onec"

    wms = await client.post("/api/integration-patterns/start", json={"pattern_id": "wms_fact_to_onec"})
    assert wms.status_code == 200, wms.text
    assert wms.json()["wizard_route"] == "/master?pattern=wms_fact_to_onec"

    multiple = await client.post("/api/integration-patterns/start", json={"pattern_id": "request_multiple_odata_response"})
    assert multiple.status_code == 200, multiple.text
    assert multiple.json()["wizard_route"] == "/master?pattern=request_multiple_odata_response"

    xml_odata = await client.post("/api/integration-patterns/start", json={"pattern_id": "xml_odata_xml_response"})
    assert xml_odata.status_code == 200, xml_odata.text
    assert xml_odata.json()["wizard_route"] == "/master?pattern=xml_odata_xml_response"

    request_print = await client.post("/api/integration-patterns/start", json={"pattern_id": "request_print"})
    assert request_print.status_code == 200, request_print.text
    assert request_print.json()["wizard_route"] == "/master?pattern=request_print"


async def test_integration_patterns_future_pattern_registered_but_not_startable(client):
    detail = await client.get("/api/integration-patterns/poll_odata_send_target")
    assert detail.status_code == 200, detail.text
    assert detail.json()["status"] == "available"
    assert detail.json()["wizard_route"] == "/master?pattern=poll_odata_send_target"
    assert detail.json()["docs_link"] == "/docs/onec/recipes/poll-odata-send-target"

    start = await client.post("/api/integration-patterns/start", json={"pattern_id": "poll_odata_send_target"})
    assert start.status_code == 200, start.text
    assert start.json()["wizard_route"] == "/master?pattern=poll_odata_send_target"


async def test_request_odata_response_preview_contractor_pattern(client):
    connector = await _create_contractor_odata_connector(client)
    payload = await _contractor_pattern_payload(client, connector["id"], slug="lookup-contractor-preview")

    response = await client.post("/api/integration-patterns/request-odata-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["endpoint"] == {"method": "POST", "url": "/api/bus/in/lookup-contractor-preview"}
    assert body["odata_request"]["template_filter"] == "ИНН eq '{{request.body.inn}}'"
    assert body["odata_request"]["rendered_filter"] == "ИНН eq '7707083893'"
    assert body["odata_result"]["Description"] == "ООО Ромашка"
    assert body["response_to_caller"]["contractor_name"] == "ООО Ромашка"


async def test_request_odata_response_create_creates_disabled_flow_test_case_and_run_test(client):
    connector = await _create_contractor_odata_connector(client)
    payload = await _contractor_pattern_payload(client, connector["id"], slug="lookup-contractor-create")

    response = await client.post("/api/integration-patterns/request-odata-response/create", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    compiled = body["compile"]
    assert compiled["success"] is True
    assert compiled["enabled"] is False
    assert compiled["endpoint"] == {"method": "POST", "url": "/api/bus/in/lookup-contractor-create"}
    assert compiled["saved_test_case_id"]

    flow = await client.get(f"/api/integration-flows/{compiled['integration_flow_id']}")
    assert flow.status_code == 200, flow.text
    flow_body = flow.json()
    assert flow_body["enabled"] is False
    step_types = [step["type"] for step in flow_body["builder_json"]["steps"]]
    assert step_types == ["odata_query", "build_payload", "return_response"]
    assert flow_body["builder_json"]["steps"][2]["response_body_type"] == "json"

    test_case = await client.get(f"/api/test-cases/{compiled['saved_test_case_id']}")
    assert test_case.status_code == 200, test_case.text
    assert test_case.json()["body_json"]["inn"] == "7707083893"

    dry_run = await client.post(
        "/api/integration-patterns/request-odata-response/run-test",
        json={"integration_flow_id": compiled["integration_flow_id"], "dry_run": True},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["success"] is True


async def test_request_odata_response_duplicate_slug_conflict(client):
    connector = await _create_contractor_odata_connector(client)
    payload = await _contractor_pattern_payload(client, connector["id"], slug="lookup-contractor-duplicate")

    first = await client.post("/api/integration-patterns/request-odata-response/create", json=payload)
    assert first.status_code == 200, first.text

    duplicate = await client.post("/api/integration-patterns/request-odata-response/create", json=payload)
    assert duplicate.status_code == 400, duplicate.text
    assert "/api/bus/in/lookup-contractor-duplicate" in duplicate.text


async def test_request_odata_response_template_missing_variable_is_friendly(client):
    connector = await _create_contractor_odata_connector(client)
    payload = await _contractor_pattern_payload(client, connector["id"], slug="lookup-contractor-missing-variable")
    payload["response"]["body"] = {"success": True, "contractor_uuid": "{{customer.Ref_Key}}"}

    response = await client.post("/api/integration-patterns/request-odata-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert any("переменная customer не создана" in error for error in body["errors"])


async def test_request_odata_response_empty_odata_result_is_friendly(client):
    connector = await _create_contractor_odata_connector(client)
    payload = await _contractor_pattern_payload(client, connector["id"], slug="lookup-contractor-empty")
    payload["input_contract"]["sample"]["inn"] = "0000000000"
    payload["input_contract"]["fields"][1]["example"] = "0000000000"

    response = await client.post("/api/integration-patterns/request-odata-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert any("Контрагент не найден по ИНН 0000000000" in error for error in body["errors"])


async def test_request_odata_send_endpoint_preview_order_pattern(client):
    connector = await _create_order_odata_connector(client)
    payload = await _order_send_endpoint_payload(client, connector["id"], slug="send-order-preview")

    response = await client.post("/api/integration-patterns/request-odata-send-endpoint/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["endpoint"] == {"method": "POST", "url": "/api/bus/in/send-order-preview"}
    assert body["odata_request"]["template_filter"] == "Number eq '{{request.body.order_number}}'"
    assert body["odata_request"]["rendered_filter"] == "Number eq '260666/6938'"
    assert body["odata_result"]["Number"] == "260666/6938"
    assert body["target_payload"]["site_code"] == "B2B"
    assert body["target_payload"]["order"]["uuid"] == "66666666-6666-6666-6666-666666666666"
    assert body["target_request"]["method"] == "POST"
    assert body["target_request"]["url"] == "http://site.local/api/orders/import"
    assert body["response_to_caller"]["proxy_response"] is True


async def test_request_odata_send_endpoint_create_creates_disabled_flow_test_case_and_run_test(client):
    connector = await _create_order_odata_connector(client)
    payload = await _order_send_endpoint_payload(client, connector["id"], slug="send-order-create")

    response = await client.post("/api/integration-patterns/request-odata-send-endpoint/create", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    compiled = body["compile"]
    assert compiled["success"] is True
    assert compiled["enabled"] is False
    assert compiled["endpoint"] == {"method": "POST", "url": "/api/bus/in/send-order-create"}
    assert compiled["saved_test_case_id"]

    flow = await client.get(f"/api/integration-flows/{compiled['integration_flow_id']}")
    assert flow.status_code == 200, flow.text
    flow_body = flow.json()
    assert flow_body["enabled"] is False
    assert flow_body["response_config_json"]["response_mode"] == "proxy_response"
    step_types = [step["type"] for step in flow_body["builder_json"]["steps"]]
    assert step_types == ["odata_query", "build_payload", "call_endpoint", "return_response"]
    assert flow_body["builder_json"]["steps"][2]["url"] == "http://site.local/api/orders/import"
    assert flow_body["builder_json"]["steps"][3]["body"] == "{{response.body}}"

    test_case = await client.get(f"/api/test-cases/{compiled['saved_test_case_id']}")
    assert test_case.status_code == 200, test_case.text
    assert test_case.json()["body_json"]["order_number"] == "260666/6938"

    dry_run = await client.post(
        "/api/integration-patterns/request-odata-send-endpoint/run-test",
        json={"integration_flow_id": compiled["integration_flow_id"], "dry_run": True},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["success"] is True


async def test_request_odata_send_endpoint_duplicate_slug_conflict(client):
    connector = await _create_order_odata_connector(client)
    payload = await _order_send_endpoint_payload(client, connector["id"], slug="send-order-duplicate")

    first = await client.post("/api/integration-patterns/request-odata-send-endpoint/create", json=payload)
    assert first.status_code == 200, first.text

    duplicate = await client.post("/api/integration-patterns/request-odata-send-endpoint/create", json=payload)
    assert duplicate.status_code == 400, duplicate.text
    assert "/api/bus/in/send-order-duplicate" in duplicate.text


async def test_request_odata_send_endpoint_payload_missing_variable_is_friendly(client):
    connector = await _create_order_odata_connector(client)
    payload = await _order_send_endpoint_payload(client, connector["id"], slug="send-order-missing-variable")
    payload["payload"]["template"] = {"source": "OMH", "order_uuid": "{{customer.Ref_Key}}"}

    response = await client.post("/api/integration-patterns/request-odata-send-endpoint/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert any("В payload используется customer.Ref_Key" in error and "переменная customer не создана" in error for error in body["errors"])


async def test_request_odata_send_endpoint_target_url_validates(client):
    connector = await _create_order_odata_connector(client)
    payload = await _order_send_endpoint_payload(client, connector["id"], slug="send-order-invalid-url")
    payload["target"]["url"] = "ftp://site.local/api/orders/import"

    response = await client.post("/api/integration-patterns/request-odata-send-endpoint/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert any("URL должен начинаться с http:// или https://" in error for error in body["errors"])


async def test_request_odata_send_endpoint_empty_order_result_is_friendly(client):
    connector = await _create_order_odata_connector(client)
    payload = await _order_send_endpoint_payload(client, connector["id"], slug="send-order-empty")
    payload["input_contract"]["sample"]["order_number"] = "000000"
    for field in payload["input_contract"]["fields"]:
        if field["path"] == "request.body.order_number":
            field["example"] = "000000"

    response = await client.post("/api/integration-patterns/request-odata-send-endpoint/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert any("Заказ не найден по номеру 000000" in error for error in body["errors"])


async def test_request_multiple_odata_response_preview_xml_order_products(client):
    connector = await _create_order_odata_connector(client)
    payload = await _multiple_odata_response_payload(client, connector["id"], slug="lookup-order-products-preview")

    response = await client.post("/api/integration-patterns/request-multiple-odata-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["endpoint"] == {"method": "POST", "url": "/api/bus/in/lookup-order-products-preview"}
    assert body["order_request"]["template_filter"] == "Number eq '{{request.body.number}}'"
    assert body["order_request"]["rendered_filter"] == "Number eq '260666/6938'"
    assert body["order_result"]["Ref_Key"] == CUSTOMER_ORDER_REF
    assert body["items_request"]["template_resource"] == "Document_ЗаказКлиента(guid'{{order.Ref_Key}}')/Товары"
    assert body["items_request"]["rendered_resource"] == f"Document_ЗаказКлиента(guid'{CUSTOMER_ORDER_REF}')/Товары"
    assert body["items_result"][0]["Номенклатура_Key"] == CUSTOMER_PRODUCT_REF
    assert body["human_steps"] == ["Получен запрос", "Найден заказ в 1С", "Прочитаны строки заказа", "Собран XML-ответ", "Ответ возвращён вызывающему сервису"]
    assert "<Response>" in body["response_to_caller"]
    assert f"<UUID>{CUSTOMER_ORDER_REF}</UUID>" in body["response_to_caller"]
    assert f"<ProductUUID>{CUSTOMER_PRODUCT_REF}</ProductUUID>" in body["response_to_caller"]
    assert body["response_to_caller"].count("<Item>") == 2


async def test_request_multiple_odata_response_create_creates_disabled_flow_test_case_and_run_test(client):
    connector = await _create_order_odata_connector(client)
    payload = await _multiple_odata_response_payload(client, connector["id"], slug="lookup-order-products-create")

    response = await client.post("/api/integration-patterns/request-multiple-odata-response/create", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    compiled = body["compile"]
    assert compiled["success"] is True
    assert compiled["enabled"] is False
    assert compiled["endpoint"] == {"method": "POST", "url": "/api/bus/in/lookup-order-products-create"}
    assert compiled["saved_test_case_id"]

    flow = await client.get(f"/api/integration-flows/{compiled['integration_flow_id']}")
    assert flow.status_code == 200, flow.text
    flow_body = flow.json()
    assert flow_body["enabled"] is False
    assert flow_body["response_config_json"]["response_mode"] == "sync_response"
    steps = flow_body["builder_json"]["steps"]
    assert [step["type"] for step in steps] == ["odata_query", "odata_query", "build_payload", "return_response"]
    assert steps[1]["source_master_type"] == "odata_object_query"
    assert steps[2]["body_type"] == "xml"
    assert steps[3]["response_body_type"] == "xml"
    assert steps[3]["body_template"] == "{{target_payload}}"

    test_case = await client.get(f"/api/test-cases/{compiled['saved_test_case_id']}")
    assert test_case.status_code == 200, test_case.text
    assert test_case.json()["body_json"]["operation"] == "lookup_order_products"

    dry_run = await client.post(
        "/api/integration-patterns/request-multiple-odata-response/run-test",
        json={"integration_flow_id": compiled["integration_flow_id"], "dry_run": True},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["success"] is True

    enabled = await client.post(f"/api/integration-master/compiled/{compiled['integration_flow_id']}/enable")
    assert enabled.status_code == 200, enabled.text
    real_run = await client.post(f"/api/test-cases/{compiled['saved_test_case_id']}/run")
    assert real_run.status_code == 200, real_run.text
    assert real_run.json()["success"] is True
    assert real_run.json()["timeline_url"]


async def test_request_multiple_odata_response_json_template_preserves_items_array(client):
    connector = await _create_order_odata_connector(client)
    payload = await _multiple_odata_response_payload(client, connector["id"], slug="lookup-order-products-json")
    payload["response"] = {
        "type": "json",
        "status_code": 200,
        "template": '{"success":true,"order":"{{order.Number}}","items":"{{items}}"}',
        "headers": {"Content-Type": "application/json"},
    }

    response = await client.post("/api/integration-patterns/request-multiple-odata-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert isinstance(body["response_to_caller"]["items"], list)
    assert body["response_to_caller"]["items"][0]["Номенклатура_Key"] == CUSTOMER_PRODUCT_REF


async def test_request_multiple_odata_response_order_not_found_is_friendly(client):
    connector = await _create_order_odata_connector(client)
    payload = await _multiple_odata_response_payload(client, connector["id"], slug="lookup-order-products-empty-order")
    payload["input_contract"]["sample"]["number"] = "000000"
    for field in payload["input_contract"]["fields"]:
        if field["path"] == "request.body.number":
            field["example"] = "000000"

    response = await client.post("/api/integration-patterns/request-multiple-odata-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert "Заказ не найден по номеру 000000. Проверьте OData-подключение, ресурс и номер заказа." in body["errors"]


async def test_request_multiple_odata_response_empty_items_is_friendly(client):
    connector = await _create_order_odata_connector(client, items=[])
    payload = await _multiple_odata_response_payload(client, connector["id"], slug="lookup-order-products-empty-items")

    response = await client.post("/api/integration-patterns/request-multiple-odata-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert "Табличная часть Товары пустая или недоступна через OData." in body["errors"]


async def test_request_multiple_odata_response_items_save_as_mismatch_is_friendly(client):
    connector = await _create_order_odata_connector(client)
    payload = await _multiple_odata_response_payload(client, connector["id"], slug="lookup-order-products-save-as-mismatch")
    payload["read_items"]["save_as"] = "rows"

    response = await client.post("/api/integration-patterns/request-multiple-odata-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert "В XML-шаблоне используется items, но шаг чтения строк сохранил результат под другим именем." in body["errors"]


async def test_request_odata_object_foreach_send_endpoint_preview_dnp_chz_pattern(client):
    connector = await _create_dnp_chz_odata_connector(client)
    payload = await _dnp_chz_pattern_payload(client, connector["id"], slug="dnp-chz-preview")

    response = await client.post("/api/integration-patterns/request-odata-object-foreach-send-endpoint/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["endpoint"] == {"method": "POST", "url": "/api/bus/in/dnp-chz-preview"}
    assert body["order_request"]["template_filter"] == "Number eq '{{request.body.Number}}'"
    assert body["order_request"]["rendered_filter"] == "Number eq '260666/6938'"
    assert body["order_result"]["Ref_Key"] == ORDER_REF
    assert body["products_result"][0]["Номенклатура_Key"] == PRODUCT_REF
    assert body["codes_summary"]["rows_found"] == 3
    assert body["codes_summary"]["odata_requests"] == 1
    assert isinstance(body["target_payload"]["payload"]["rows"], list)
    assert len(body["target_payload"]["payload"]["rows"]) == 3
    assert body["target_payload"]["payload"]["rows"][0]["ПолныйКодМаркировки"] == "0104607009529011215DnP001"
    assert body["target_payload"]["payload"]["order_numbers_by_basis"] == {ORDER_REF: "260666/6938"}
    assert body["target_request"]["method"] == "POST"
    assert body["target_request"]["url"] == "http://172.16.3.10/api/v2/integrations/omh/chz/codes/import"
    assert body["response_to_caller"] == {"ok": True}


async def test_request_odata_object_foreach_send_endpoint_create_creates_disabled_flow_and_run_test(client):
    connector = await _create_dnp_chz_odata_connector(client)
    payload = await _dnp_chz_pattern_payload(client, connector["id"], slug="dnp-chz-create")

    response = await client.post("/api/integration-patterns/request-odata-object-foreach-send-endpoint/create", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    compiled = body["compile"]
    assert compiled["success"] is True
    assert compiled["enabled"] is False
    assert compiled["endpoint"] == {"method": "POST", "url": "/api/bus/in/dnp-chz-create"}
    assert compiled["saved_test_case_id"]

    flow = await client.get(f"/api/integration-flows/{compiled['integration_flow_id']}")
    assert flow.status_code == 200, flow.text
    flow_body = flow.json()
    assert flow_body["enabled"] is False
    assert flow_body["response_config_json"]["response_mode"] == "sync_response"
    steps = flow_body["builder_json"]["steps"]
    assert [step["type"] for step in steps] == ["odata_query", "odata_query", "foreach", "build_payload", "call_endpoint", "return_response"]
    assert steps[1]["source_master_type"] == "odata_object_query"
    assert steps[2]["source_master_type"] == "foreach_odata"
    assert steps[2]["step"]["top"] == 500
    assert steps[2]["step"]["paginate"] is True
    assert steps[4]["url"] == "http://172.16.3.10/api/v2/integrations/omh/chz/codes/import"
    assert steps[5]["body"] == {"ok": True}

    test_case = await client.get(f"/api/test-cases/{compiled['saved_test_case_id']}")
    assert test_case.status_code == 200, test_case.text
    assert test_case.json()["body_json"]["sinc"] == "dnp_sinc_pull_codes"

    dry_run = await client.post(
        "/api/integration-patterns/request-odata-object-foreach-send-endpoint/run-test",
        json={"integration_flow_id": compiled["integration_flow_id"], "dry_run": True},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["success"] is True


async def test_request_odata_object_foreach_send_endpoint_duplicate_slug_conflict(client):
    connector = await _create_dnp_chz_odata_connector(client)
    payload = await _dnp_chz_pattern_payload(client, connector["id"], slug="dnp-chz-duplicate")

    first = await client.post("/api/integration-patterns/request-odata-object-foreach-send-endpoint/create", json=payload)
    assert first.status_code == 200, first.text

    duplicate = await client.post("/api/integration-patterns/request-odata-object-foreach-send-endpoint/create", json=payload)
    assert duplicate.status_code == 400, duplicate.text
    assert "/api/bus/in/dnp-chz-duplicate" in duplicate.text


async def test_request_odata_object_foreach_send_endpoint_rejects_foreach_top_above_500(client):
    connector = await _create_dnp_chz_odata_connector(client)
    payload = await _dnp_chz_pattern_payload(client, connector["id"], slug="dnp-chz-top-limit")
    payload["find_codes"]["top"] = 501

    response = await client.post("/api/integration-patterns/request-odata-object-foreach-send-endpoint/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert any("$top не может быть больше 500" in error for error in body["errors"])


async def test_request_odata_object_foreach_send_endpoint_empty_codes_is_friendly(client):
    connector = await _create_dnp_chz_odata_connector(client, codes=[])
    payload = await _dnp_chz_pattern_payload(client, connector["id"], slug="dnp-chz-empty-codes")

    response = await client.post("/api/integration-patterns/request-odata-object-foreach-send-endpoint/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert any("По продукции не найдено кодов Честного знака" in error for error in body["errors"])


async def test_training_mock_dnp_chz_codes_success_and_error(client):
    ok = await client.post(
        "/api/training/mock-dnp/chz/codes/import",
        json={"payload": {"order_name": "26-0666/6938", "rows": [{"ПолныйКодМаркировки": "0104607009529011215DnP001"}]}},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["ok"] is True
    assert ok.json()["rows_count"] == 1
    assert ok.json()["dnp_request_id"] == "DNP-CHZ-TRAINING-0001"

    empty = await client.post("/api/training/mock-dnp/chz/codes/import", json={"payload": {"order_name": "26-0666/6938", "rows": []}})
    assert empty.status_code == 422
    assert empty.json()["error"] == "DNP_CHZ_ROWS_REQUIRED"

    error = await client.post(
        "/api/training/mock-dnp/chz/codes/import",
        json={"payload": {"order_name": "ERROR-500", "rows": [{"ПолныйКодМаркировки": "0104607009529011215DnP001"}]}},
    )
    assert error.status_code == 500
    assert error.json()["error"] == "DNP_CHZ_IMPORT_FAILED"


async def test_source_web_api_writeback_onec_preview_order_pattern(client):
    connector = await _create_order_odata_connector(client)
    payload = await _source_web_api_writeback_payload(client, connector["id"], slug="publish-order-preview")

    response = await client.post("/api/integration-patterns/source-web-api-writeback-onec/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["endpoint"] == {"method": "POST", "url": "/api/bus/in/publish-order-preview"}
    assert body["odata_request"]["template_filter"] == "Number eq '{{request.body.order_number}}'"
    assert body["odata_request"]["rendered_filter"] == "Number eq '260666/6938'"
    assert body["odata_result"]["Number"] == "260666/6938"
    assert body["site_payload"]["order"]["uuid"] == "66666666-6666-6666-6666-666666666666"
    assert body["site_request"]["url"] == "http://site.local/api/orders/import"
    assert body["site_request"]["save_response_as"] == "site_response"
    assert body["extraction"]["external_id"] == "SITE-ORDER-260666-6938"
    assert body["onec_writeback_payload"]["external_id"] == "SITE-ORDER-260666-6938"
    assert body["onec_writeback_request"]["url"] == "http://1c-server/erp/hs/omh/order-external-id"
    assert body["response_to_caller"]["onec_writeback_success"] is True


async def test_source_web_api_writeback_onec_create_creates_disabled_flow_and_run_test(client):
    connector = await _create_order_odata_connector(client)
    payload = await _source_web_api_writeback_payload(client, connector["id"], slug="publish-order-create")

    response = await client.post("/api/integration-patterns/source-web-api-writeback-onec/create", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    compiled = body["compile"]
    assert compiled["success"] is True
    assert compiled["enabled"] is False
    assert compiled["endpoint"] == {"method": "POST", "url": "/api/bus/in/publish-order-create"}
    assert compiled["saved_test_case_id"]

    flow = await client.get(f"/api/integration-flows/{compiled['integration_flow_id']}")
    assert flow.status_code == 200, flow.text
    flow_body = flow.json()
    assert flow_body["enabled"] is False
    assert flow_body["target_type"] == "onec"
    assert flow_body["action_json"]["type"] == "call_1c_http_service"
    steps = flow_body["builder_json"]["steps"]
    assert [step["type"] for step in steps] == ["odata_query", "build_payload", "call_endpoint", "condition", "condition", "build_payload", "call_endpoint", "return_response"]
    assert steps[2]["save_response_as"] == "site_response"
    assert steps[4]["if"] == "site_response.external_id exists"
    assert steps[6]["url"] == "http://1c-server/erp/hs/omh/order-external-id"
    assert steps[6]["save_response_as"] == "onec_writeback_response"

    test_case = await client.get(f"/api/test-cases/{compiled['saved_test_case_id']}")
    assert test_case.status_code == 200, test_case.text
    assert test_case.json()["body_json"]["operation"] == "publish_order_to_site"

    dry_run = await client.post(
        "/api/integration-patterns/source-web-api-writeback-onec/run-test",
        json={"integration_flow_id": compiled["integration_flow_id"], "dry_run": True},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["success"] is True


async def test_source_web_api_writeback_onec_duplicate_slug_conflict(client):
    connector = await _create_order_odata_connector(client)
    payload = await _source_web_api_writeback_payload(client, connector["id"], slug="publish-order-duplicate")

    first = await client.post("/api/integration-patterns/source-web-api-writeback-onec/create", json=payload)
    assert first.status_code == 200, first.text

    duplicate = await client.post("/api/integration-patterns/source-web-api-writeback-onec/create", json=payload)
    assert duplicate.status_code == 400, duplicate.text
    assert "/api/bus/in/publish-order-duplicate" in duplicate.text


async def test_source_web_api_writeback_onec_validation_errors_are_friendly(client):
    connector = await _create_order_odata_connector(client)
    payload = await _source_web_api_writeback_payload(client, connector["id"], slug="publish-order-validation")

    payload["site_payload"]["template"] = {"source": "OMH", "order_uuid": "{{customer.Ref_Key}}"}
    site_payload = await client.post("/api/integration-patterns/source-web-api-writeback-onec/preview", json=payload)
    assert site_payload.status_code == 200, site_payload.text
    assert site_payload.json()["valid"] is False
    assert any("переменная customer не создана" in error for error in site_payload.json()["errors"])

    payload = await _source_web_api_writeback_payload(client, connector["id"], slug="publish-order-missing-external-id")
    payload["site_response_extraction"]["sample_response"] = {"success": True, "status": "accepted"}
    extraction = await client.post("/api/integration-patterns/source-web-api-writeback-onec/preview", json=payload)
    assert extraction.status_code == 200, extraction.text
    assert extraction.json()["valid"] is False
    assert any("нет external_id" in error for error in extraction.json()["errors"])

    payload = await _source_web_api_writeback_payload(client, connector["id"], slug="publish-order-site-rejected")
    payload["site_response_extraction"]["sample_response"] = {"success": False, "error_code": "SITE_REJECTED_ORDER", "error_message": "Training site rejected order"}
    site_rejected = await client.post("/api/integration-patterns/source-web-api-writeback-onec/preview", json=payload)
    assert site_rejected.status_code == 200, site_rejected.text
    assert site_rejected.json()["valid"] is False
    assert any("Внешний сайт не принял данные" in error for error in site_rejected.json()["errors"])

    payload = await _source_web_api_writeback_payload(client, connector["id"], slug="publish-order-writeback-invalid")
    payload["onec_writeback_payload"]["template"]["external_id"] = "{{site_response.missing_id}}"
    writeback_payload = await client.post("/api/integration-patterns/source-web-api-writeback-onec/preview", json=payload)
    assert writeback_payload.status_code == 200, writeback_payload.text
    assert writeback_payload.json()["valid"] is False
    assert any("site_response.missing_id" in error for error in writeback_payload.json()["errors"])

    payload = await _source_web_api_writeback_payload(client, connector["id"], slug="publish-order-invalid-onec-url")
    payload["onec_http_service"]["url"] = "ftp://1c-server/erp/hs/omh/order-external-id"
    onec_url = await client.post("/api/integration-patterns/source-web-api-writeback-onec/preview", json=payload)
    assert onec_url.status_code == 200, onec_url.text
    assert onec_url.json()["valid"] is False
    assert any("URL 1С HTTP service должен начинаться" in error for error in onec_url.json()["errors"])


async def test_training_mock_site_and_onec_writeback(client):
    ok = await client.post(
        "/api/training/mock-site/orders/import",
        json={"source": "OMH", "site_code": "B2B", "order": {"number": "260666/6938", "uuid": "66666666-6666-6666-6666-666666666666"}},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["success"] is True
    assert ok.json()["external_id"] == "SITE-ORDER-260666-6938"

    rejected = await client.post(
        "/api/training/mock-site/orders/import",
        json={"source": "OMH", "site_code": "ERROR", "order": {"number": "260666/6938"}},
    )
    assert rejected.status_code == 400
    assert rejected.json()["error_code"] == "SITE_REJECTED_ORDER"

    writeback = await client.post(
        "/api/training/mock-onec/hs/omh/order-external-id",
        json={"order_ref_key": "66666666-6666-6666-6666-666666666666", "external_id": "SITE-ORDER-260666-6938"},
    )
    assert writeback.status_code == 200, writeback.text
    assert writeback.json() == {"success": True, "message": "External id saved"}

    onec_error = await client.post("/api/training/mock-onec/hs/omh/order-external-id", json={"external_id": "ERROR"})
    assert onec_error.status_code == 500
    assert onec_error.json()["error"] == "ONEC_WRITEBACK_FAILED"


async def test_training_mock_onec_shipment_facts_success_and_business_error(client):
    ok = await client.post(
        "/api/training/mock-onec/hs/omh/shipment-facts",
        json={
            "payload": {
                "order_number": "260666/6938",
                "wms_shipment_id": "WMS-SHIP-123",
                "items": [{"sku": "ABC-123", "qty": 10}],
            }
        },
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["success"] is True
    assert ok.json()["external_document_id"] == "1C-SHIP-WMS-SHIP-123"

    business_error = await client.post(
        "/api/training/mock-onec/hs/omh/shipment-facts",
        json={
            "payload": {
                "order_number": "404",
                "wms_shipment_id": "WMS-SHIP-404",
                "items": [{"sku": "ABC-123", "qty": 10}],
            }
        },
    )
    assert business_error.status_code == 200, business_error.text
    assert business_error.json()["success"] is False
    assert business_error.json()["error_code"] == "ORDER_NOT_FOUND"


async def test_wms_fact_to_onec_preview_shipment_pattern(client):
    connector = await _create_order_odata_connector(client)
    payload = await _wms_fact_to_onec_payload(client, connector["id"], slug="wms-shipment-preview")

    response = await client.post("/api/integration-patterns/wms-fact-to-onec/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["endpoint"] == {"method": "POST", "url": "/api/bus/in/wms-shipment-preview"}
    assert body["odata_request"]["template_filter"] == "Number eq '{{request.body.order_number}}'"
    assert body["odata_request"]["rendered_filter"] == "Number eq '260666/6938'"
    assert body["odata_result"]["Number"] == "260666/6938"
    assert body["onec_payload"]["payload"]["order_ref_key"] == CUSTOMER_ORDER_REF
    assert body["onec_payload"]["payload"]["items"] == [{"sku": "ABC-123", "qty": 10, "barcode": "04646151697384"}]
    assert body["onec_request"]["method"] == "POST"
    assert body["onec_request"]["url"] == "http://1c-server/erp/hs/omh/shipment-facts"
    assert body["onec_request"]["body_preview"]["payload"]["items"][0]["qty"] == 10
    assert body["response_to_caller"]["onec_response"]["success"] is True
    assert body["human_steps"] == ["Получен складской факт от WMS: отгрузка", "Найден заказ в 1С", "Собран payload для 1С", "Отправлено в 1С HTTP service", "Ответ 1С возвращён WMS"]


async def test_wms_fact_to_onec_create_creates_disabled_flow_and_run_test(client):
    connector = await _create_order_odata_connector(client)
    payload = await _wms_fact_to_onec_payload(client, connector["id"], slug="wms-shipment-create")

    response = await client.post("/api/integration-patterns/wms-fact-to-onec/create", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    compiled = body["compile"]
    assert compiled["success"] is True
    assert compiled["enabled"] is False
    assert compiled["endpoint"] == {"method": "POST", "url": "/api/bus/in/wms-shipment-create"}
    assert compiled["saved_test_case_id"]

    flow = await client.get(f"/api/integration-flows/{compiled['integration_flow_id']}")
    assert flow.status_code == 200, flow.text
    flow_body = flow.json()
    assert flow_body["enabled"] is False
    assert flow_body["source_type"] == "wms"
    assert flow_body["target_type"] == "onec"
    assert flow_body["action_json"]["type"] == "call_1c_http_service"
    assert flow_body["action_json"]["operation"] == "update_shipment_status"
    steps = flow_body["builder_json"]["steps"]
    assert [step["type"] for step in steps] == ["odata_query", "build_payload", "call_endpoint", "return_response"]
    assert steps[2]["path"] == "/shipment-facts"
    assert steps[2]["save_response_as"] == "onec_response"

    test_case = await client.get(f"/api/test-cases/{compiled['saved_test_case_id']}")
    assert test_case.status_code == 200, test_case.text
    assert test_case.json()["body_json"]["operation"] == "shipment_fact"

    dry_run = await client.post(
        "/api/integration-patterns/wms-fact-to-onec/run-test",
        json={"integration_flow_id": compiled["integration_flow_id"], "dry_run": True},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["success"] is True


async def test_wms_fact_to_onec_duplicate_slug_conflict(client):
    connector = await _create_order_odata_connector(client)
    payload = await _wms_fact_to_onec_payload(client, connector["id"], slug="wms-shipment-duplicate")

    first = await client.post("/api/integration-patterns/wms-fact-to-onec/create", json=payload)
    assert first.status_code == 200, first.text

    duplicate = await client.post("/api/integration-patterns/wms-fact-to-onec/create", json=payload)
    assert duplicate.status_code == 400, duplicate.text
    assert "/api/bus/in/wms-shipment-duplicate" in duplicate.text


async def test_wms_fact_to_onec_optional_odata_disabled_uses_order_ref_key(client):
    connector = await _create_order_odata_connector(client)
    payload = await _wms_fact_to_onec_payload(client, connector["id"], slug="wms-shipment-no-odata")
    payload["input_contract"]["sample"]["order_ref_key"] = "request-order-ref-key"
    payload["odata_lookup"]["enabled"] = False

    response = await client.post("/api/integration-patterns/wms-fact-to-onec/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["odata_request"]["enabled"] is False
    assert body["onec_payload"]["payload"]["order_ref_key"] == "request-order-ref-key"


async def test_wms_fact_to_onec_stock_balance_without_odata_creates_flow(client):
    connector = await _create_order_odata_connector(client)
    payload = await _wms_stock_balance_to_onec_payload(client, connector["id"], slug="wms-stock-create")

    preview = await client.post("/api/integration-patterns/wms-fact-to-onec/preview", json=payload)

    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    assert preview_body["valid"] is True
    assert preview_body["odata_request"] == {"enabled": False, "order_ref_key_path": "request.body.order_ref_key", "save_as": "order", "order_ref_key_required": False}
    assert preview_body["onec_payload"]["payload"]["stock_balance_id"] == "WMS-STOCK-20260713-001"
    assert preview_body["onec_request"]["url"] == "http://1c-server/erp/hs/omh/stock-balances"
    assert preview_body["human_steps"][0] == "Получен складской факт от WMS: остатки"
    assert preview_body["human_steps"][1] == "OData lookup заказа пропущен"

    created = await client.post("/api/integration-patterns/wms-fact-to-onec/create", json=payload)

    assert created.status_code == 200, created.text
    flow = await client.get(f"/api/integration-flows/{created.json()['compile']['integration_flow_id']}")
    assert flow.status_code == 200, flow.text
    steps = flow.json()["builder_json"]["steps"]
    assert [step["type"] for step in steps] == ["build_payload", "call_endpoint", "return_response"]
    assert steps[1]["operation"] == "update_stock_balance"
    assert steps[1]["path"] == "/stock-balances"


async def test_wms_fact_to_onec_validation_errors_are_friendly(client):
    connector = await _create_order_odata_connector(client)
    payload = await _wms_fact_to_onec_payload(client, connector["id"], slug="wms-shipment-missing-items")
    payload["input_contract"]["sample"].pop("items")

    missing_items = await client.post("/api/integration-patterns/wms-fact-to-onec/preview", json=payload)
    assert missing_items.status_code == 200, missing_items.text
    assert missing_items.json()["valid"] is False
    assert any("нет массива items" in error for error in missing_items.json()["errors"])

    payload = await _wms_fact_to_onec_payload(client, connector["id"], slug="wms-shipment-missing-qty")
    payload["input_contract"]["sample"]["items"] = [{"sku": "ABC-123"}]
    missing_qty = await client.post("/api/integration-patterns/wms-fact-to-onec/preview", json=payload)
    assert missing_qty.status_code == 200, missing_qty.text
    assert missing_qty.json()["valid"] is False
    assert any("items[0]" in error and "qty" in error for error in missing_qty.json()["errors"])

    payload = await _wms_fact_to_onec_payload(client, connector["id"], slug="wms-shipment-business-error")
    payload["onec_http_service"]["mock_response_json"] = {"success": False, "error_code": "ORDER_NOT_FOUND", "error_message": "Заказ не найден в 1С"}
    business_error = await client.post("/api/integration-patterns/wms-fact-to-onec/preview", json=payload)
    assert business_error.status_code == 200, business_error.text
    business_body = business_error.json()
    assert business_body["valid"] is True
    assert business_body["response_to_caller"]["onec_response"]["success"] is False
    assert any("1С вернула бизнес-ошибку" in warning for warning in business_body["warnings"])


async def test_xml_raw_bridge_keeps_body_hash(client):
    payload = await _xml_raw_bridge_payload(client, slug="onec-xml-raw-preview")

    response = await client.post("/api/integration-patterns/xml-raw-bridge/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["endpoint"] == {"method": "POST", "url": "/api/bus/in/onec-xml-raw-preview"}
    assert body["target_request"]["body_preview"] == payload["input_contract"]["sample"]
    assert body["hash_check"]["original_sha256"] == body["hash_check"]["forwarded_sha256"]
    assert body["hash_check"]["unchanged"] is True
    assert "/Документ/Номер" in {item["path"] for item in body["xml_paths"]}
    assert body["response_to_caller"]["success"] is True


async def test_xml_raw_bridge_create_creates_disabled_flow_and_run_test(client):
    payload = await _xml_raw_bridge_payload(client, slug="onec-xml-raw-create")

    response = await client.post("/api/integration-patterns/xml-raw-bridge/create", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    compiled = body["compile"]
    assert compiled["success"] is True
    assert compiled["enabled"] is False
    assert compiled["endpoint"] == {"method": "POST", "url": "/api/bus/in/onec-xml-raw-create"}
    assert compiled["saved_test_case_id"]

    flow = await client.get(f"/api/integration-flows/{compiled['integration_flow_id']}")
    assert flow.status_code == 200, flow.text
    flow_body = flow.json()
    assert flow_body["enabled"] is False
    assert flow_body["source_type"] == "onec"
    assert flow_body["target_type"] == "onec"
    steps = flow_body["builder_json"]["steps"]
    assert [step["type"] for step in steps] == ["raw_xml_forward", "return_response"]
    assert steps[0]["training_mock_onec_xml_receiver"] is True
    assert steps[0]["verify_hash"] is True

    test_case = await client.get(f"/api/test-cases/{compiled['saved_test_case_id']}")
    assert test_case.status_code == 200, test_case.text
    assert test_case.json()["input_mode"] == "xml"
    assert test_case.json()["body_text"] == payload["input_contract"]["sample"]

    dry_run = await client.post(
        "/api/integration-patterns/xml-raw-bridge/run-test",
        json={"integration_flow_id": compiled["integration_flow_id"], "dry_run": True},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["success"] is True

    enabled = await client.post(f"/api/integration-master/compiled/{compiled['integration_flow_id']}/enable")
    assert enabled.status_code == 200, enabled.text

    live = await client.post("/api/bus/in/onec-xml-raw-create", content=payload["input_contract"]["sample"].encode("utf-8"), headers={"Content-Type": "application/xml"})
    assert live.status_code == 200, live.text
    live_body = live.json()
    assert live_body["success"] is True
    assert live_body["response"]["document_number"] == "123"

    timeline = await client.get(live_body["timeline_url"].replace("/events/", "/api/events/") + "/timeline")
    assert timeline.status_code == 200, timeline.text
    artifact_names = _timeline_artifact_names(timeline.json())
    assert {"raw_xml_original.xml", "raw_xml_forwarded.xml", "xml_hashes.json", "target_request.json", "target_response.json"}.issubset(artifact_names)


async def test_xml_raw_bridge_duplicate_slug_conflict(client):
    payload = await _xml_raw_bridge_payload(client, slug="onec-xml-raw-duplicate")

    first = await client.post("/api/integration-patterns/xml-raw-bridge/create", json=payload)
    assert first.status_code == 200, first.text

    duplicate = await client.post("/api/integration-patterns/xml-raw-bridge/create", json=payload)
    assert duplicate.status_code == 400, duplicate.text
    assert "/api/bus/in/onec-xml-raw-duplicate" in duplicate.text


async def test_xml_raw_bridge_invalid_xml_policy(client):
    payload = await _xml_raw_bridge_payload(client, slug="onec-xml-raw-invalid")
    payload["input_contract"]["sample"] = "<Документ><Номер>123</Документ>"
    payload["input_contract"]["fields"] = []

    invalid = await client.post("/api/integration-patterns/xml-raw-bridge/preview", json=payload)
    assert invalid.status_code == 200, invalid.text
    assert invalid.json()["valid"] is False
    assert any("XML не удалось разобрать" in error for error in invalid.json()["errors"])

    payload["raw_xml_policy"]["require_valid_xml"] = False
    payload["raw_xml_policy"]["validate_xml"] = False
    allowed = await client.post("/api/integration-patterns/xml-raw-bridge/preview", json=payload)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["valid"] is True
    assert any("validation выключен" in warning for warning in allowed.json()["warnings"])


async def test_xml_raw_bridge_target_error_preserves_original_response(client):
    payload = await _xml_raw_bridge_payload(client, slug="onec-xml-raw-error", document_number="ERROR")
    created = await client.post("/api/integration-patterns/xml-raw-bridge/create", json=payload)
    assert created.status_code == 200, created.text
    flow_id = created.json()["compile"]["integration_flow_id"]
    enabled = await client.post(f"/api/integration-master/compiled/{flow_id}/enable")
    assert enabled.status_code == 200, enabled.text

    live = await client.post("/api/bus/in/onec-xml-raw-error", content=payload["input_contract"]["sample"].encode("utf-8"), headers={"Content-Type": "application/xml"})

    assert live.status_code == 200, live.text
    body = live.json()
    assert body["success"] is False
    assert body["response"]["body"]["error_code"] == "XML_DOCUMENT_REJECTED"
    assert body["external_error"]["body"]["error_code"] == "XML_DOCUMENT_REJECTED"


async def test_xml_odata_xml_response_preview_order_lookup(client):
    connector = await _create_order_odata_connector(client)
    payload = await _xml_odata_xml_response_payload(client, connector["id"], slug="xml-order-preview")

    response = await client.post("/api/integration-patterns/xml-odata-xml-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["endpoint"] == {"method": "POST", "url": "/api/bus/in/xml-order-preview"}
    assert body["extracted_variables"]["order_number"] == "260666/6938"
    assert body["odata_request"]["template_filter"] == "Number eq '{{order_number}}'"
    assert body["odata_request"]["rendered_filter"] == "Number eq '260666/6938'"
    assert body["odata_result"]["Number"] == "260666/6938"
    assert "<UUID>" in body["response_to_caller"]
    assert CUSTOMER_ORDER_REF in body["response_to_caller"]


async def test_xml_odata_xml_response_create_creates_disabled_flow_and_run_test(client):
    connector = await _create_order_odata_connector(client)
    payload = await _xml_odata_xml_response_payload(client, connector["id"], slug="xml-order-create")

    response = await client.post("/api/integration-patterns/xml-odata-xml-response/create", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    compiled = body["compile"]
    assert compiled["success"] is True
    assert compiled["enabled"] is False
    assert compiled["endpoint"] == {"method": "POST", "url": "/api/bus/in/xml-order-create"}
    assert compiled["saved_test_case_id"]

    flow = await client.get(f"/api/integration-flows/{compiled['integration_flow_id']}")
    assert flow.status_code == 200, flow.text
    flow_body = flow.json()
    assert flow_body["enabled"] is False
    assert flow_body["source_type"] == "external_api"
    assert flow_body["target_type"] == "internal"
    steps = flow_body["builder_json"]["steps"]
    assert [step["type"] for step in steps] == ["xml_extract", "odata_query", "build_payload", "return_response"]
    assert steps[0]["raw_artifact_name"] == "raw_xml_input.xml"
    assert steps[1]["filter"] == "Number eq '{{order_number}}'"
    assert steps[2]["response_artifacts"] is True

    test_case = await client.get(f"/api/test-cases/{compiled['saved_test_case_id']}")
    assert test_case.status_code == 200, test_case.text
    assert test_case.json()["input_mode"] == "xml"
    assert "<Number>260666/6938</Number>" in test_case.json()["body_text"]

    dry_run = await client.post(
        "/api/integration-patterns/xml-odata-xml-response/run-test",
        json={"integration_flow_id": compiled["integration_flow_id"], "dry_run": True},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["success"] is True

    enabled = await client.post(f"/api/integration-master/compiled/{compiled['integration_flow_id']}/enable")
    assert enabled.status_code == 200, enabled.text

    live = await client.post("/api/bus/in/xml-order-create", content=payload["input_contract"]["sample"].encode("utf-8"), headers={"Content-Type": "application/xml"})
    assert live.status_code == 200, live.text
    live_body = live.json()
    assert live_body["success"] is True
    assert CUSTOMER_ORDER_REF in live_body["response"]
    assert live_body["response_meta"]["response_body_type"] == "xml"

    timeline = await client.get(live_body["timeline_url"].replace("/events/", "/api/events/") + "/timeline")
    assert timeline.status_code == 200, timeline.text
    artifact_names = _timeline_artifact_names(timeline.json())
    assert {"raw_xml_input.xml", "xml_extracted_fields.json", "odata_query_request.json", "odata_query_response.json", "response_template.xml", "rendered_response.xml"}.issubset(artifact_names)


async def test_xml_odata_xml_response_duplicate_slug_conflict(client):
    connector = await _create_order_odata_connector(client)
    payload = await _xml_odata_xml_response_payload(client, connector["id"], slug="xml-order-duplicate")

    first = await client.post("/api/integration-patterns/xml-odata-xml-response/create", json=payload)
    assert first.status_code == 200, first.text

    duplicate = await client.post("/api/integration-patterns/xml-odata-xml-response/create", json=payload)
    assert duplicate.status_code == 400, duplicate.text
    assert "/api/bus/in/xml-order-duplicate" in duplicate.text


async def test_xml_odata_xml_response_missing_xml_path_is_friendly(client):
    connector = await _create_order_odata_connector(client)
    payload = await _xml_odata_xml_response_payload(client, connector["id"], slug="xml-order-missing-path")
    payload["input_contract"]["sample"] = payload["input_contract"]["sample"].replace("<Number>260666/6938</Number>", "")

    response = await client.post("/api/integration-patterns/xml-odata-xml-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert any("В XML не найдено поле /Request/Number" in error for error in body["errors"])


async def test_xml_odata_xml_response_odata_empty_is_friendly(client):
    connector = await _create_order_odata_connector(client)
    payload = await _xml_odata_xml_response_payload(client, connector["id"], slug="xml-order-empty")
    payload["input_contract"]["sample"] = payload["input_contract"]["sample"].replace("260666/6938", "NOT-FOUND")

    response = await client.post("/api/integration-patterns/xml-odata-xml-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert any("Заказ не найден по номеру NOT-FOUND" in error for error in body["errors"])


async def test_xml_odata_xml_response_escapes_xml_values(client):
    connector = await _create_order_odata_connector(
        client,
        orders=[
            {"Ref_Key": CUSTOMER_ORDER_REF, "Number": "260666/6938", "Date": "2026-07-12T12:00:00", "Posted": True, "Note": "A&B <C>"},
        ],
        items=[],
    )
    payload = await _xml_odata_xml_response_payload(client, connector["id"], slug="xml-order-escape")
    payload["response"]["template"] = "<Response><Number>{{order.Number}}</Number><Note>{{order.Note}}</Note></Response>"
    payload["odata_step"]["select"].append("Note")

    response = await client.post("/api/integration-patterns/xml-odata-xml-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert "<Note>A&amp;B &lt;C&gt;</Note>" in body["response_to_caller"]


async def test_xml_odata_xml_response_invalid_xml_response_is_friendly(client):
    connector = await _create_order_odata_connector(client)
    payload = await _xml_odata_xml_response_payload(client, connector["id"], slug="xml-order-invalid-response")
    payload["response"]["template"] = "<Response><Order>{{order.Number}}</Response>"

    response = await client.post("/api/integration-patterns/xml-odata-xml-response/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is False
    assert any("Не удалось собрать XML-ответ" in error for error in body["errors"])


async def test_request_print_preview_renders_zpl(client):
    await _create_training_printer_connector(client)
    payload = await _request_print_payload(client, slug="print-labels-preview")

    response = await client.post("/api/integration-patterns/request-print/preview", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["endpoint"] == {"method": "POST", "url": "/api/bus/in/print-labels-preview"}
    assert body["selected_printer"]["name"] == "TRAINING-PRINTER-01"
    assert body["selected_printer"]["type"] == "training_mock"
    assert body["labels_count"] == 2
    assert "^FDПлата ABC^FS" in body["rendered_zpl_first_label"]
    assert "^FD#1 / ORDER-123^FS" in body["rendered_zpl_first_label"]
    assert body["response_to_caller"]["labels_count"] == 2
    assert body["response_to_caller"]["status"] == "dry_run"


async def test_request_print_create_creates_disabled_flow_and_run_test(client):
    await _create_training_printer_connector(client)
    payload = await _request_print_payload(client, slug="print-labels-create")

    response = await client.post("/api/integration-patterns/request-print/create", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    compiled = body["compile"]
    assert compiled["success"] is True
    assert compiled["enabled"] is False
    assert compiled["endpoint"] == {"method": "POST", "url": "/api/bus/in/print-labels-create"}
    assert compiled["saved_test_case_id"]

    flow = await client.get(f"/api/integration-flows/{compiled['integration_flow_id']}")
    assert flow.status_code == 200, flow.text
    flow_body = flow.json()
    assert flow_body["enabled"] is False
    assert flow_body["source_type"] == "onec"
    assert flow_body["target_type"] == "printer"
    steps = flow_body["builder_json"]["steps"]
    assert [step["type"] for step in steps] == ["print_labels", "return_response"]
    assert steps[0]["labels"]["path"] == "request.body.labels"
    assert steps[0]["print_mode"] == "dry_run"

    test_case = await client.get(f"/api/test-cases/{compiled['saved_test_case_id']}")
    assert test_case.status_code == 200, test_case.text
    assert test_case.json()["body_json"]["labels"][0]["code"] == "010464615169738421ABC"

    dry_run = await client.post(
        "/api/integration-patterns/request-print/run-test",
        json={"integration_flow_id": compiled["integration_flow_id"], "dry_run": True},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["success"] is True

    enabled = await client.post(f"/api/integration-master/compiled/{compiled['integration_flow_id']}/enable")
    assert enabled.status_code == 200, enabled.text

    live = await client.post("/api/bus/in/print-labels-create", json=payload["input_contract"]["sample"])
    assert live.status_code == 200, live.text
    live_body = live.json()
    assert live_body["success"] is True
    assert live_body["response"]["printer"] == "TRAINING-PRINTER-01"
    assert live_body["response"]["labels_count"] == 2
    assert live_body["response"]["status"] == "dry_run"

    timeline = await client.get(live_body["timeline_url"].replace("/events/", "/api/events/") + "/timeline")
    assert timeline.status_code == 200, timeline.text
    artifact_names = _timeline_artifact_names(timeline.json())
    assert {
        "incoming_print_request.json",
        "selected_printer.json",
        "zpl_template.zpl",
        "rendered_zpl_first_label.zpl",
        "rendered_zpl_all_labels.zpl",
        "printer_request.json",
        "printer_response.json",
    }.issubset(artifact_names)


async def test_request_print_duplicate_slug_conflict(client):
    await _create_training_printer_connector(client)
    payload = await _request_print_payload(client, slug="print-labels-duplicate")

    first = await client.post("/api/integration-patterns/request-print/create", json=payload)
    assert first.status_code == 200, first.text

    duplicate = await client.post("/api/integration-patterns/request-print/create", json=payload)
    assert duplicate.status_code == 400, duplicate.text
    assert "/api/bus/in/print-labels-duplicate" in duplicate.text


async def test_request_print_missing_labels_and_code_are_friendly(client):
    await _create_training_printer_connector(client)
    payload = await _request_print_payload(client, slug="print-labels-missing")
    del payload["input_contract"]["sample"]["labels"]

    missing_labels = await client.post("/api/integration-patterns/request-print/preview", json=payload)
    assert missing_labels.status_code == 200, missing_labels.text
    assert missing_labels.json()["valid"] is False
    assert any("В запросе нет массива labels[]" in error for error in missing_labels.json()["errors"])

    payload = await _request_print_payload(client, slug="print-labels-missing-code")
    del payload["input_contract"]["sample"]["labels"][0]["code"]
    missing_code = await client.post("/api/integration-patterns/request-print/preview", json=payload)
    assert missing_code.status_code == 200, missing_code.text
    assert missing_code.json()["valid"] is False
    assert any("В labels[0] нет поля code" in error for error in missing_code.json()["errors"])


async def test_request_print_printer_not_found_and_offline_are_friendly(client):
    payload = await _request_print_payload(client, slug="print-labels-no-printer")
    response = await client.post("/api/integration-patterns/request-print/preview", json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["valid"] is False
    assert any("Принтер TRAINING-PRINTER-01 не найден" in error for error in response.json()["errors"])

    await _create_training_printer_connector(client)
    offline = await _request_print_payload(client, slug="print-labels-offline", printer="TRAINING-OFFLINE")
    test_print = await client.post("/api/integration-patterns/request-print/test-print", json={**offline, "dry_run": False, "limit": 1})
    assert test_print.status_code == 200, test_print.text
    result = test_print.json()["print_result"]
    assert result["success"] is False
    assert result["body"]["error_code"] == "PRINTER_OFFLINE"
    assert result["body"]["error"] == "TRAINING_PRINTER_OFFLINE"


async def test_training_mock_external_api_order_import(client):
    ok = await client.post(
        "/api/training/mock-external-api/orders/import",
        json={"source": "OMH", "site_code": "B2B", "order": {"number": "260666/6938", "uuid": "66666666-6666-6666-6666-666666666666"}},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["success"] is True
    assert ok.json()["external_id"] == "TRAIN-ORDER-001"

    error = await client.post("/api/training/mock-external-api/orders/import", json={"order": {"number": "ERROR-500"}})
    assert error.status_code == 500
    assert error.json()["error"] == "TRAINING_EXTERNAL_API_ERROR"


async def test_poll_odata_send_target_preview_create_and_manual_runs(client):
    connector = await _create_order_odata_connector(
        client,
        orders=[
            {"Ref_Key": CUSTOMER_ORDER_REF, "Number": "260666/6938", "Date": "2026-07-12T12:00:00", "Posted": True, "Контрагент_Key": "11111111-1111-1111-1111-111111111111"},
            {"Ref_Key": "44444444-4444-4444-4444-444444444444", "Number": "SO-1001", "Date": "2026-07-01T10:00:00", "Posted": True, "Контрагент_Key": "11111111-1111-1111-1111-111111111111"},
            {"Ref_Key": "55555555-5555-5555-5555-555555555555", "Number": "SO-1002", "Date": "2026-07-02T11:30:00", "Posted": False, "Контрагент_Key": "22222222-2222-2222-2222-222222222222"},
        ],
    )
    payload = _poll_odata_send_target_payload(connector["id"], slug="poll-orders-wms")

    preview = await client.post("/api/integration-patterns/poll-odata-send-target/preview", json=payload)
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    assert preview_body["valid"] is True
    assert preview_body["schedule"]["type"] == "manual_only"
    assert "2026-01-01T00:00:00" in preview_body["first_run_filter"]
    assert len(preview_body["odata_result"]) == 2
    assert isinstance(preview_body["target_payload"]["payload"]["orders"], list)
    assert preview_body["target_payload"]["payload"]["count"] == 2
    assert preview_body["target_request"]["url"] == "/api/training/mock-wms/orders/import"

    created = await client.post("/api/integration-patterns/poll-odata-send-target/create", json=payload)
    assert created.status_code == 200, created.text
    created_body = created.json()
    assert created_body["enabled"] is False
    assert created_body["run_now_url"].startswith("/api/polling-jobs/")
    job_id = created_body["polling_job_id"]

    job = await client.get(f"/api/polling-jobs/{job_id}")
    assert job.status_code == 200, job.text
    job_body = job.json()
    assert job_body["enabled"] is False
    assert job_body["slug"] == "poll-orders-wms"
    assert job_body["schedule_type"] == "manual_only"
    assert job_body["integration_flow_id"] == created_body["integration_flow_id"]

    dry_run = await client.post(
        "/api/integration-patterns/poll-odata-send-target/run-test",
        json={"polling_job_id": job_id, "dry_run": True, "update_cursor": False},
    )
    assert dry_run.status_code == 200, dry_run.text
    dry_body = dry_run.json()
    assert dry_body["success"] is True
    assert dry_body["run"]["items_read"] == 2
    assert dry_body["run"]["sent_count"] == 0
    assert dry_body["run"]["cursor_after_json"] == {}
    assert dry_body["run"]["details_json"]["target_result"]["dry_run"] is True

    real_run = await client.post(f"/api/polling-jobs/{job_id}/run-now", json={"dry_run": False, "update_cursor": True})
    assert real_run.status_code == 200, real_run.text
    run_body = real_run.json()
    assert run_body["status"] == "success"
    assert run_body["items_read"] == 2
    assert run_body["sent_count"] == 2
    assert run_body["details_json"]["target_result"]["response"]["accepted_count"] == 2
    assert run_body["cursor_before_json"] == {}
    assert run_body["cursor_after_json"]["last_success_at"]

    job_after = await client.get(f"/api/polling-jobs/{job_id}")
    assert job_after.status_code == 200, job_after.text
    assert job_after.json()["cursor_json"]["last_success_at"] == run_body["cursor_after_json"]["last_success_at"]

    runs = await client.get(f"/api/polling-jobs/{job_id}/runs")
    assert runs.status_code == 200, runs.text
    assert len(runs.json()) == 2


async def test_poll_odata_send_target_empty_and_target_error(client):
    empty_connector = await _create_order_odata_connector(client, orders=[], name="Training OData Empty")
    empty_payload = _poll_odata_send_target_payload(empty_connector["id"], slug="poll-empty-orders")

    empty_run = await client.post(
        "/api/integration-patterns/poll-odata-send-target/run-test",
        json={"pattern": empty_payload, "dry_run": False, "update_cursor": False},
    )
    assert empty_run.status_code == 200, empty_run.text
    empty_body = empty_run.json()
    assert empty_body["success"] is True
    assert empty_body["run"]["items_read"] == 0
    assert empty_body["run"]["sent_count"] == 0
    assert empty_body["run"]["details_json"]["target_result"]["skipped"] is True
    assert empty_body["run"]["details_json"]["target_payload"] is None

    error_connector = await _create_order_odata_connector(
        client,
        orders=[{"Ref_Key": CUSTOMER_ORDER_REF, "Number": "ERROR-500", "Date": "2026-07-12T12:00:00", "Posted": True}],
        name="Training OData Error",
    )
    error_payload = _poll_odata_send_target_payload(error_connector["id"], slug="poll-target-error")
    error_payload["payload"]["template"] = {"order_number": "ERROR-500", "orders": "{{orders}}"}
    error_payload["target"]["url"] = "/api/training/mock-external-api/orders/import"

    error_run = await client.post(
        "/api/integration-patterns/poll-odata-send-target/run-test",
        json={"pattern": error_payload, "dry_run": False, "update_cursor": True},
    )
    assert error_run.status_code == 200, error_run.text
    error_body = error_run.json()
    assert error_body["success"] is False
    assert error_body["run"]["status"] == "failed"
    assert "Внешний API вернул ошибку" in error_body["run"]["error_message"]
    assert error_body["run"]["cursor_after_json"] == {}
    target_result = error_body["run"]["details_json"]["target_result"]
    assert target_result["status_code"] == 500
    assert target_result["response"]["error"] == "TRAINING_EXTERNAL_API_ERROR"
    assert error_body["run"]["details_json"]["cursor_not_updated"] is True


def _poll_odata_send_target_payload(connection_id: str, *, slug: str) -> dict:
    return {
        "job": {
            "name": "Sync 1C orders to WMS",
            "slug": slug,
            "enabled_after_create": False,
            "schedule_type": "manual_only",
            "interval_minutes": 5,
        },
        "odata_step": {
            "type": "odata_query",
            "connection_id": connection_id,
            "connection_name": "Training OData ERP",
            "resource": "Document_ЗаказКлиента",
            "filter_mode": "raw",
            "filter": "Date ge datetime'{{cursor.last_success_at}}' and Posted eq true",
            "select": ["Ref_Key", "Number", "Date", "Posted", "Контрагент_Key"],
            "top": 100,
            "orderby": None,
            "paginate": True,
            "save_as": "orders",
            "required": False,
        },
        "first_run": {"strategy": "fixed_start_date", "fixed_start_at": "2026-01-01T00:00:00", "hours": 24},
        "cursor": {"cursor_type": "last_success_at", "source_field": "orders[].Date", "update_when": "target_success"},
        "payload": {
            "type": "build_payload",
            "body_type": "json",
            "save_as": "target_payload",
            "json_mode": "raw_template",
            "template": {
                "omh": {
                    "run_id": "{{context.run_id}}",
                    "event_type": "ODataPollingOrders",
                    "source_system": "1C ERP",
                    "target_system": "WMS",
                },
                "payload": {
                    "orders": "{{orders}}",
                    "cursor_from": "{{cursor.last_success_at}}",
                    "count": "{{orders.length}}",
                },
            },
            "fields": [],
            "dynamic_entries": [],
            "overwrite": True,
        },
        "target": {
            "method": "POST",
            "url": "/api/training/mock-wms/orders/import",
            "headers": {"Content-Type": "application/json"},
            "body_source": "target_payload",
            "body_type": "json",
            "timeout_seconds": 30,
            "empty_result_behavior": "do_nothing_success",
        },
    }


async def _create_contractor_odata_connector(client):
    response = await client.post(
        "/api/connectors",
        json={
            "name": "Training OData ERP",
            "connector_type": "onec",
            "direction": "bidirectional",
            "config_json": {
                "base_url": "http://mock-1c.local/odata/standard.odata",
                "auth": {"type": "none"},
                "odata": {"enabled": True},
                "mock_odata": {
                    "Catalog_Контрагенты": [
                        {"Ref_Key": "31f41075-2da4-11f1-8388-000c29b755c7", "Description": "ООО Ромашка", "ИНН": "7707083893", "КПП": "770701001"},
                    ]
                },
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _create_order_odata_connector(client, *, items: list[dict] | None = None, orders: list[dict] | None = None, name: str = "Training OData ERP"):
    response = await client.post(
        "/api/connectors",
        json={
            "name": name,
            "connector_type": "onec",
            "direction": "bidirectional",
            "config_json": {
                "base_url": "http://mock-1c.local/odata/standard.odata",
                "auth": {"type": "none"},
                "odata": {"enabled": True},
                "mock_odata": {
                    "Document_ЗаказКлиента": orders
                    if orders is not None
                    else [
                        {
                            "Ref_Key": CUSTOMER_ORDER_REF,
                            "Number": "260666/6938",
                            "Date": "2026-07-12T12:00:00",
                            "Posted": True,
                        },
                    ],
                    f"Document_ЗаказКлиента(guid'{CUSTOMER_ORDER_REF}')/Товары": items
                    if items is not None
                    else [
                        {"Номенклатура_Key": CUSTOMER_PRODUCT_REF, "Количество": 2, "Цена": 120.5, "Сумма": 241.0},
                        {"Номенклатура_Key": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "Количество": 1, "Цена": 77.0, "Сумма": 77.0},
                    ],
                },
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _create_dnp_chz_odata_connector(client, *, codes: list[dict] | None = None):
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
                        {"Ref_Key": ORDER_REF, "Number": "260666/6938", "Date": "2026-04-29T16:38:53", "Posted": True, "DeletionMark": False},
                    ],
                    f"Document_ЗаказНаПроизводство2_2(guid'{ORDER_REF}')/Продукция": [
                        {"Номенклатура_Key": PRODUCT_REF, "Количество": 180, "КоличествоУпаковок": 180},
                    ],
                    "InformationRegister_ПулКодовМаркировкиСУЗ": codes if codes is not None else [_dnp_chz_code_row(1), _dnp_chz_code_row(2), _dnp_chz_code_row(3)],
                },
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _dnp_chz_code_row(index: int) -> dict:
    return {
        "КодМаркировки": f"CHZ-{index:03d}",
        "ПолныйКодМаркировки": f"0104607009529011215DnP{index:03d}",
        "ХешСуммаКодаМаркировки": f"hash-{index:03d}",
        "Статус": "emitted",
        "Организация_Key": "org-001",
        "СтанцияУправленияЗаказами_Key": "suz-001",
        "Номенклатура_Key": PRODUCT_REF,
        "Характеристика_Key": "char-001",
        "ДатаЭмиссииУниверсальная": f"2026-04-29T17:0{index}:00",
        "ДатаПечатиУниверсальная": None,
        "ШтрихкодУпаковки_Key": "pack-001",
        "GTIN": "04607009529011",
        "МаксимальнаяРозничнаяЦена": 0,
        "СпособВводаВОборот": "Производство",
        "Шаблон": "default",
        "ХешСуммаУпаковки": f"pack-hash-{index:03d}",
        "ТипШтрихкода": "DataMatrix",
        "МаркировкаОстатков": False,
        "СрокГодности": "2027-04-29",
        "ЗаказНаЭмиссию_Key": "emission-001",
        "ИдентификаторЗаказаСУЗ": "SUZ-ORDER-001",
        "ИдентификаторБлокаСУЗ": "SUZ-BLOCK-001",
        "ВидКИЗ": "unit",
        "РазмерКИЗ": "standard",
        "ДокументОснование": ORDER_REF,
        "ДокументОснование_Type": "Document_ЗаказНаПроизводство2_2",
    }


async def _contractor_pattern_payload(client, connection_id: str, *, slug: str):
    parse = await client.post(
        "/api/integration-master/input/parse",
        json={
            "input_mode": "json",
            "scenario_key": "external_contractor_lookup",
            "sample": {"operation": "lookup_contractor", "inn": "7707083893"},
        },
    )
    assert parse.status_code == 200, parse.text
    parse_result = parse.json()
    return {
        "name": "Lookup contractor by INN",
        "slug": slug,
        "input_contract": {
            "name": "Lookup contractor by INN",
            "slug": slug,
            "input_mode": "json",
            "source_system": "external_api",
            "scenario_key": "external_contractor_lookup",
            "sample": parse_result["normalized_sample"],
            "fields": parse_result["fields"],
            "operation_key": {
                "type": "field",
                "field_path": "request.body.operation",
                "value": "lookup_contractor",
                "fallback_paths": [],
                "matcher_preview": {"mode": "any", "rules": [{"type": "body_path_equals", "path": "operation", "value": "lookup_contractor"}]},
            },
            "business_key": {"path": "request.body.inn", "fallback_paths": []},
        },
        "odata_step": {
            "type": "odata_query",
            "connection_id": connection_id,
            "resource": "Catalog_Контрагенты",
            "filter_mode": "builder",
            "filter_rule": {"field": "ИНН", "operator": "eq", "value_type": "variable", "value": "request.body.inn"},
            "select": ["Ref_Key", "Description", "ИНН", "КПП"],
            "top": 1,
            "orderby": None,
            "paginate": False,
            "save_as": "contractor",
            "required": True,
        },
        "response": {
            "type": "json",
            "status_code": 200,
            "body": {
                "success": True,
                "contractor_uuid": "{{contractor.Ref_Key}}",
                "contractor_name": "{{contractor.Description}}",
                "inn": "{{contractor.ИНН}}",
                "kpp": "{{contractor.КПП}}",
            },
        },
    }


async def _order_send_endpoint_payload(client, connection_id: str, *, slug: str):
    parse = await client.post(
        "/api/integration-master/input/parse",
        json={
            "input_mode": "json",
            "scenario_key": "onec_publish_order_to_site",
            "sample": {"operation": "send_order_to_site", "order_number": "260666/6938", "site_code": "B2B"},
        },
    )
    assert parse.status_code == 200, parse.text
    parse_result = parse.json()
    return {
        "name": "Send order to site",
        "slug": slug,
        "input_contract": {
            "name": "Send order to site",
            "slug": slug,
            "input_mode": "json",
            "source_system": "onec",
            "scenario_key": "onec_publish_order_to_site",
            "sample": parse_result["normalized_sample"],
            "fields": parse_result["fields"],
            "operation_key": {
                "type": "field",
                "field_path": "request.body.operation",
                "value": "send_order_to_site",
                "fallback_paths": [],
                "matcher_preview": {"mode": "any", "rules": [{"type": "body_path_equals", "path": "operation", "value": "send_order_to_site"}]},
            },
            "business_key": {"path": "request.body.order_number", "fallback_paths": []},
        },
        "odata_step": {
            "type": "odata_query",
            "connection_id": connection_id,
            "resource": "Document_ЗаказКлиента",
            "filter_mode": "builder",
            "filter_rule": {"field": "Number", "operator": "eq", "value_type": "variable", "value": "request.body.order_number"},
            "select": ["Ref_Key", "Number", "Date", "Posted"],
            "top": 1,
            "orderby": None,
            "paginate": False,
            "save_as": "order",
            "required": True,
        },
        "payload": {
            "type": "build_payload",
            "body_type": "json",
            "save_as": "target_payload",
            "json_mode": "raw_template",
            "template": {
                "source": "OMH",
                "site_code": "{{request.body.site_code}}",
                "order": {
                    "uuid": "{{order.Ref_Key}}",
                    "number": "{{order.Number}}",
                    "date": "{{order.Date}}",
                    "posted": "{{order.Posted}}",
                },
            },
            "fields": [],
            "dynamic_entries": [],
            "overwrite": True,
        },
        "target": {
            "method": "POST",
            "url": "http://site.local/api/orders/import",
            "headers": {"Content-Type": "application/json"},
            "body_source": "target_payload",
            "body_type": "json",
            "timeout_seconds": 20,
        },
        "response_to_caller": {"type": "proxy_response", "status_code": 200, "body": None, "headers": {}},
    }


async def _multiple_odata_response_payload(client, connection_id: str, *, slug: str):
    parse = await client.post(
        "/api/integration-master/input/parse",
        json={
            "input_mode": "json",
            "scenario_key": "external_order_lookup_xml_response",
            "sample": {"operation": "lookup_order_products", "number": "260666/6938", "format": "xml"},
        },
    )
    assert parse.status_code == 200, parse.text
    parse_result = parse.json()
    return {
        "name": "Внешний сервис спрашивает заказ из 1С",
        "slug": slug,
        "input_contract": {
            "name": "Внешний сервис спрашивает заказ из 1С",
            "slug": slug,
            "input_mode": "json",
            "source_system": "external_api",
            "scenario_key": "external_order_lookup_xml_response",
            "sample": parse_result["normalized_sample"],
            "fields": parse_result["fields"],
            "operation_key": {
                "type": "field",
                "field_path": "request.body.operation",
                "value": "lookup_order_products",
                "fallback_paths": [],
                "matcher_preview": {"mode": "any", "rules": [{"type": "body_path_equals", "path": "operation", "value": "lookup_order_products"}]},
            },
            "business_key": {"path": "request.body.number", "fallback_paths": []},
        },
        "find_order": {
            "type": "odata_query",
            "connection_id": connection_id,
            "resource": "Document_ЗаказКлиента",
            "filter_mode": "raw",
            "filter_rule": {"field": "Number", "operator": "eq", "value_type": "variable", "value": "request.body.number"},
            "filter": "Number eq '{{request.body.number}}'",
            "select": ["Ref_Key", "Number", "Date", "Posted"],
            "top": 1,
            "orderby": None,
            "paginate": False,
            "save_as": "order",
            "required": True,
        },
        "read_items": {
            "type": "odata_object_query",
            "connection_id": connection_id,
            "object_variable": "order",
            "key_field": "Ref_Key",
            "key_type": "guid",
            "base_resource": "Document_ЗаказКлиента",
            "nested_resource": "Товары",
            "resource_template": "Document_ЗаказКлиента(guid'{{order.Ref_Key}}')/Товары",
            "filter": None,
            "select": ["Номенклатура_Key", "Количество", "Цена", "Сумма"],
            "top": 100,
            "paginate": False,
            "save_as": "items",
            "required": True,
            "overwrite": True,
        },
        "response": {
            "type": "xml",
            "status_code": 200,
            "template": """<Response>
  <Success>true</Success>
  <Order>
    <UUID>{{order.Ref_Key}}</UUID>
    <Number>{{order.Number}}</Number>
    <Date>{{order.Date}}</Date>
    <Posted>{{order.Posted}}</Posted>
  </Order>
  <Items>
    {{#items}}
    <Item>
      <ProductUUID>{{Номенклатура_Key}}</ProductUUID>
      <Quantity>{{Количество}}</Quantity>
      <Price>{{Цена}}</Price>
      <Amount>{{Сумма}}</Amount>
    </Item>
    {{/items}}
  </Items>
</Response>""",
            "headers": {"Content-Type": "application/xml; charset=utf-8"},
        },
    }


async def _source_web_api_writeback_payload(client, connection_id: str, *, slug: str):
    parse = await client.post(
        "/api/integration-master/input/parse",
        json={
            "input_mode": "json",
            "scenario_key": "onec_publish_order_to_site",
            "sample": {"operation": "publish_order_to_site", "order_number": "260666/6938", "site_code": "B2B"},
        },
    )
    assert parse.status_code == 200, parse.text
    parse_result = parse.json()
    return {
        "name": "Отправить данные на сайт и записать ответ обратно в 1С",
        "slug": slug,
        "input_contract": {
            "name": "Отправить данные на сайт и записать ответ обратно в 1С",
            "slug": slug,
            "input_mode": "json",
            "source_system": "onec",
            "scenario_key": "onec_publish_order_to_site",
            "sample": parse_result["normalized_sample"],
            "fields": parse_result["fields"],
            "operation_key": {
                "type": "field",
                "field_path": "request.body.operation",
                "value": "publish_order_to_site",
                "fallback_paths": [],
                "matcher_preview": {"mode": "any", "rules": [{"type": "body_path_equals", "path": "operation", "value": "publish_order_to_site"}]},
            },
            "business_key": {"path": "request.body.order_number", "fallback_paths": []},
        },
        "odata_step": {
            "type": "odata_query",
            "connection_id": connection_id,
            "resource": "Document_ЗаказКлиента",
            "filter_mode": "raw",
            "filter_rule": {"field": "Number", "operator": "eq", "value_type": "variable", "value": "request.body.order_number"},
            "filter": "Number eq '{{request.body.order_number}}'",
            "select": ["Ref_Key", "Number", "Date", "Posted"],
            "top": 1,
            "orderby": None,
            "paginate": False,
            "save_as": "order",
            "required": True,
        },
        "site_payload": {
            "type": "build_payload",
            "body_type": "json",
            "save_as": "site_payload",
            "json_mode": "raw_template",
            "template": {
                "source": "OMH",
                "site_code": "{{request.body.site_code}}",
                "order": {
                    "uuid": "{{order.Ref_Key}}",
                    "number": "{{order.Number}}",
                    "date": "{{order.Date}}",
                    "posted": "{{order.Posted}}",
                },
            },
            "fields": [],
            "dynamic_entries": [],
            "overwrite": True,
        },
        "site_endpoint": {
            "method": "POST",
            "url": "http://site.local/api/orders/import",
            "headers": {"Content-Type": "application/json"},
            "body_source": "site_payload",
            "body_type": "json",
            "timeout_seconds": 20,
            "save_response_as": "site_response",
        },
        "site_response_extraction": {
            "external_id_path": "site_response.external_id",
            "status_path": "site_response.status",
            "success_condition": {"path": "site_response.success", "operator": "eq", "value": True},
            "sample_response": {"success": True, "external_id": "SITE-ORDER-260666-6938", "status": "accepted"},
        },
        "onec_writeback_payload": {
            "type": "build_payload",
            "body_type": "json",
            "save_as": "onec_writeback_payload",
            "json_mode": "raw_template",
            "template": {
                "order_ref_key": "{{order.Ref_Key}}",
                "order_number": "{{order.Number}}",
                "external_system": "{{request.body.site_code}}",
                "external_id": "{{site_response.external_id}}",
                "status": "{{site_response.status}}",
            },
            "fields": [],
            "dynamic_entries": [],
            "overwrite": True,
        },
        "onec_http_service": {
            "method": "POST",
            "connector_id": None,
            "connector_name": None,
            "base_url": "http://1c-server/erp/hs/omh",
            "path": "/order-external-id",
            "url": "",
            "headers": {"Content-Type": "application/json"},
            "body_source": "onec_writeback_payload",
            "body_type": "json",
            "timeout_seconds": 20,
            "save_response_as": "onec_writeback_response",
        },
        "caller_response": {
            "type": "custom_json",
            "status_code": 200,
            "body": {
                "success": True,
                "order_number": "{{order.Number}}",
                "external_id": "{{site_response.external_id}}",
                "site_status": "{{site_response.status}}",
                "onec_writeback_success": "{{onec_writeback_response.success}}",
            },
            "headers": {"Content-Type": "application/json"},
        },
    }


async def _wms_fact_to_onec_payload(client, connection_id: str, *, slug: str):
    sample = {
        "operation": "shipment_fact",
        "wms_shipment_id": "WMS-SHIP-123",
        "order_number": "260666/6938",
        "status": "shipped",
        "warehouse_code": "MAIN",
        "shipped_at": "2026-07-04T14:30:00",
        "items": [{"sku": "ABC-123", "qty": 10, "barcode": "04646151697384"}],
    }
    parse = await client.post(
        "/api/integration-master/input/parse",
        json={
            "input_mode": "json",
            "scenario_key": "wms_shipment_fact",
            "sample": sample,
        },
    )
    assert parse.status_code == 200, parse.text
    parse_result = parse.json()
    return {
        "name": "WMS отправляет складской факт в 1С",
        "slug": slug,
        "input_contract": {
            "name": "WMS отправляет складской факт в 1С",
            "slug": slug,
            "input_mode": "json",
            "source_system": "wms",
            "scenario_key": "wms_shipment_fact",
            "sample": parse_result["normalized_sample"],
            "fields": parse_result["fields"],
            "operation_key": {
                "type": "field",
                "field_path": "request.body.operation",
                "value": "shipment_fact",
                "fallback_paths": [],
                "matcher_preview": {"mode": "any", "rules": [{"type": "body_path_equals", "path": "operation", "value": "shipment_fact"}]},
            },
            "business_key": {"path": "request.body.wms_shipment_id", "fallback_paths": ["request.body.order_number"]},
        },
        "odata_lookup": {
            "enabled": True,
            "config": {
                "type": "odata_query",
                "connection_id": connection_id,
                "resource": "Document_ЗаказКлиента",
                "filter_mode": "raw",
                "filter_rule": {"field": "Number", "operator": "eq", "value_type": "variable", "value": "request.body.order_number"},
                "filter": "Number eq '{{request.body.order_number}}'",
                "select": ["Ref_Key", "Number", "Date", "Posted"],
                "top": 1,
                "orderby": None,
                "paginate": False,
                "save_as": "order",
                "required": True,
            },
            "order_ref_key_path": "request.body.order_ref_key",
        },
        "onec_payload": {
            "type": "build_payload",
            "body_type": "json",
            "save_as": "onec_payload",
            "json_mode": "raw_template",
            "template": {
                "omh": {
                    "event_id": "{{context.event_id}}",
                    "run_id": "{{context.run_id}}",
                    "correlation_id": "wms-shipment:{{request.body.wms_shipment_id}}",
                    "event_type": "WmsShipmentFactReceived",
                    "entity_type": "ShipmentFact",
                    "entity_id": "{{request.body.wms_shipment_id}}",
                    "source_system": "WMS",
                    "target_system": "1C ERP",
                },
                "payload": {
                    "order_ref_key": "{{order.Ref_Key}}",
                    "order_number": "{{request.body.order_number}}",
                    "wms_shipment_id": "{{request.body.wms_shipment_id}}",
                    "status": "{{request.body.status}}",
                    "warehouse_code": "{{request.body.warehouse_code}}",
                    "shipped_at": "{{request.body.shipped_at}}",
                    "items": "{{request.body.items}}",
                },
            },
            "fields": [],
            "dynamic_entries": [],
            "overwrite": True,
        },
        "onec_http_service": {
            "method": "POST",
            "connector_id": None,
            "connector_name": None,
            "operation": "update_shipment_status",
            "base_url": "http://1c-server/erp/hs/omh",
            "path": "/shipment-facts",
            "url": "",
            "headers": {"Content-Type": "application/json"},
            "body_source": "onec_payload",
            "body_type": "json",
            "timeout_seconds": 30,
            "save_response_as": "onec_response",
        },
        "caller_response": {
            "type": "normalized",
            "status_code": 200,
            "body": {
                "success": "{{onec_response.success}}",
                "wms_shipment_id": "{{request.body.wms_shipment_id}}",
                "order_number": "{{request.body.order_number}}",
                "onec_response": "{{onec_response}}",
            },
            "headers": {"Content-Type": "application/json"},
        },
    }


async def _wms_stock_balance_to_onec_payload(client, connection_id: str, *, slug: str):
    sample = {
        "operation": "stock_balance",
        "stock_balance_id": "WMS-STOCK-20260713-001",
        "warehouse_code": "MAIN",
        "moment": "2026-07-13T10:00:00",
        "items": [{"sku": "A-100", "quantity": 125.5, "uom": "pcs", "batch": "B-001", "cell": "A-01-01"}],
    }
    parse = await client.post(
        "/api/integration-master/input/parse",
        json={
            "input_mode": "json",
            "scenario_key": "wms_shipment_fact",
            "sample": sample,
        },
    )
    assert parse.status_code == 200, parse.text
    parse_result = parse.json()
    return {
        "name": "WMS отправляет складской факт в 1С",
        "slug": slug,
        "input_contract": {
            "name": "WMS отправляет складской факт в 1С",
            "slug": slug,
            "input_mode": "json",
            "source_system": "wms",
            "scenario_key": "wms_shipment_fact",
            "sample": parse_result["normalized_sample"],
            "fields": parse_result["fields"],
            "operation_key": {
                "type": "field",
                "field_path": "request.body.operation",
                "value": "stock_balance",
                "fallback_paths": [],
                "matcher_preview": {"mode": "any", "rules": [{"type": "body_path_equals", "path": "operation", "value": "stock_balance"}]},
            },
            "business_key": {"path": "request.body.stock_balance_id", "fallback_paths": ["request.body.warehouse_code"]},
        },
        "odata_lookup": {
            "enabled": False,
            "config": {
                "type": "odata_query",
                "connection_id": connection_id,
                "resource": "Document_ЗаказКлиента",
                "filter_mode": "raw",
                "filter_rule": {"field": "Number", "operator": "eq", "value_type": "variable", "value": "request.body.order_number"},
                "filter": "Number eq '{{request.body.order_number}}'",
                "select": ["Ref_Key", "Number", "Date", "Posted"],
                "top": 1,
                "orderby": None,
                "paginate": False,
                "save_as": "order",
                "required": True,
            },
            "order_ref_key_path": "request.body.order_ref_key",
        },
        "onec_payload": {
            "type": "build_payload",
            "body_type": "json",
            "save_as": "onec_payload",
            "json_mode": "raw_template",
            "template": {
                "omh": {
                    "event_id": "{{context.event_id}}",
                    "run_id": "{{context.run_id}}",
                    "correlation_id": "wms-stock:{{request.body.stock_balance_id}}",
                    "event_type": "WmsStockBalanceReceived",
                    "entity_type": "StockBalance",
                    "entity_id": "{{request.body.stock_balance_id}}",
                    "source_system": "WMS",
                    "target_system": "1C ERP",
                },
                "payload": {
                    "stock_balance_id": "{{request.body.stock_balance_id}}",
                    "warehouse_code": "{{request.body.warehouse_code}}",
                    "moment": "{{request.body.moment}}",
                    "items": "{{request.body.items}}",
                },
            },
            "fields": [],
            "dynamic_entries": [],
            "overwrite": True,
        },
        "onec_http_service": {
            "method": "POST",
            "connector_id": None,
            "connector_name": None,
            "operation": "update_stock_balance",
            "base_url": "http://1c-server/erp/hs/omh",
            "path": "/stock-balances",
            "url": "",
            "headers": {"Content-Type": "application/json"},
            "body_source": "onec_payload",
            "body_type": "json",
            "timeout_seconds": 30,
            "save_response_as": "onec_response",
        },
        "caller_response": {
            "type": "normalized",
            "status_code": 200,
            "body": {
                "success": "{{onec_response.success}}",
                "stock_balance_id": "{{request.body.stock_balance_id}}",
                "onec_response": "{{onec_response}}",
            },
            "headers": {"Content-Type": "application/json"},
        },
    }


async def _xml_odata_xml_response_payload(client, connection_id: str, *, slug: str):
    sample = """<Request>
  <Operation>lookup_order</Operation>
  <Number>260666/6938</Number>
  <Format>xml</Format>
</Request>"""
    parse = await client.post(
        "/api/integration-master/input/parse",
        json={
            "input_mode": "xml",
            "scenario_key": "xml_input_odata_xml_response",
            "sample": sample,
        },
    )
    assert parse.status_code == 200, parse.text
    parse_result = parse.json()
    return {
        "name": "XML lookup order",
        "slug": slug,
        "input_contract": {
            "name": "XML lookup order",
            "slug": slug,
            "input_mode": "xml",
            "source_system": "external_api",
            "scenario_key": "xml_input_odata_xml_response",
            "sample": parse_result["normalized_sample"],
            "fields": parse_result["fields"],
            "operation_key": {
                "type": "field",
                "field_path": "xml./Request/Operation",
                "value": "lookup_order",
                "fallback_paths": [],
                "matcher_preview": {"mode": "any", "rules": [{"type": "xml_path_equals", "path": "Request.Operation", "value": "lookup_order"}]},
            },
            "business_key": {"path": "xml./Request/Number", "fallback_paths": []},
            "endpoint_url": f"/api/bus/in/{slug}",
        },
        "xml_extract": {
            "fields": [
                {"name": "operation", "path": "/Request/Operation", "required": True, "mode": "first", "example": "lookup_order"},
                {"name": "order_number", "path": "/Request/Number", "required": True, "mode": "first", "example": "260666/6938"},
                {"name": "format", "path": "/Request/Format", "required": False, "mode": "first", "example": "xml"},
            ]
        },
        "odata_step": {
            "type": "odata_query",
            "connection_id": connection_id,
            "connection_name": "Training OData ERP",
            "resource": "Document_ЗаказКлиента",
            "filter_mode": "raw",
            "filter_rule": {"field": "Number", "operator": "eq", "value_type": "variable", "value": "order_number"},
            "filter": "Number eq '{{order_number}}'",
            "select": ["Ref_Key", "Number", "Date", "Posted"],
            "top": 1,
            "orderby": None,
            "paginate": False,
            "save_as": "order",
            "required": True,
        },
        "response": {
            "body_type": "xml",
            "status_code": 200,
            "template": """<Response>
  <Success>true</Success>
  <Order>
    <UUID>{{order.Ref_Key}}</UUID>
    <Number>{{order.Number}}</Number>
    <Date>{{order.Date}}</Date>
    <Posted>{{order.Posted}}</Posted>
  </Order>
</Response>""",
            "headers": {"Content-Type": "application/xml; charset=utf-8"},
        },
    }


async def _xml_raw_bridge_payload(client, *, slug: str, document_number: str = "123"):
    sample = f"""<Документ>
  <Тип>УПД</Тип>
  <Номер>{document_number}</Номер>
  <ИНН>7707083893</ИНН>
  <Дата>2026-07-04</Дата>
</Документ>"""
    parse = await client.post(
        "/api/integration-master/input/parse",
        json={
            "input_mode": "xml",
            "scenario_key": "onec_xml_raw_bridge",
            "sample": sample,
        },
    )
    assert parse.status_code == 200, parse.text
    parse_result = parse.json()
    return {
        "name": "XML без изменений → endpoint / 1С",
        "slug": slug,
        "input_contract": {
            "name": "XML без изменений → endpoint / 1С",
            "slug": slug,
            "input_mode": "xml",
            "source_system": "onec",
            "scenario_key": "onec_xml_raw_bridge",
            "sample": parse_result["normalized_sample"],
            "fields": parse_result["fields"],
            "operation_key": {
                "type": "endpoint",
                "field_path": None,
                "value": None,
                "fallback_paths": [],
                "matcher_preview": {"mode": "endpoint", "rules": []},
            },
            "business_key": {"path": "xml./Документ/Номер", "fallback_paths": []},
            "endpoint_url": f"/api/bus/in/{slug}",
        },
        "raw_xml_policy": {
            "forward_unchanged": True,
            "require_valid_xml": True,
            "validate_xml": True,
            "verify_hash": True,
        },
        "target": {
            "mode": "raw_url",
            "connector_id": None,
            "connector_name": None,
            "method": "POST",
            "base_url": "http://training.local/hs/omh",
            "path": "/receive-upd-xml",
            "url": "http://training.local/hs/omh/receive-upd-xml",
            "headers": {"Content-Type": "application/xml; charset=utf-8"},
            "timeout_seconds": 30,
            "save_response_as": "target_response",
            "training_mock_onec_xml_receiver": True,
        },
        "caller_response": {
            "type": "proxy_target_response",
            "status_code": 200,
            "body": {"success": True},
            "headers": {"Content-Type": "application/json"},
        },
    }


async def _create_training_printer_connector(client):
    response = await client.post(
        "/api/connectors",
        json={
            "name": "Training Printer",
            "connector_type": "rest",
            "direction": "target",
            "config_json": {"url": "http://training.local/mock-printer/print", "method": "POST", "training_mock_printer": True},
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _request_print_payload(client, *, slug: str, printer: str = "TRAINING-PRINTER-01"):
    sample = {
        "operation": "print_labels",
        "printer": printer,
        "job_key": "ORDER-123",
        "labels": [
            {"sequence_no": 1, "sku": "ABC-123", "title": "Плата ABC", "code": "010464615169738421ABC", "qty": 1},
            {"sequence_no": 2, "sku": "XYZ-777", "title": "Модуль XYZ", "code": "010464615169738421XYZ", "qty": 1},
        ],
    }
    parse = await client.post(
        "/api/integration-master/input/parse",
        json={
            "input_mode": "json",
            "scenario_key": "onec_print_request",
            "sample": sample,
        },
    )
    assert parse.status_code == 200, parse.text
    parse_result = parse.json()
    return {
        "name": "Print labels",
        "slug": slug,
        "input_contract": {
            "name": "Print labels",
            "slug": slug,
            "input_mode": "json",
            "source_system": "onec",
            "scenario_key": "onec_print_request",
            "sample": parse_result["normalized_sample"],
            "fields": parse_result["fields"],
            "operation_key": {
                "type": "field",
                "field_path": "request.body.operation",
                "value": "print_labels",
                "fallback_paths": [],
                "matcher_preview": {"mode": "any", "rules": [{"type": "body_path_equals", "path": "operation", "value": "print_labels"}]},
            },
            "business_key": {"path": "request.body.job_key", "fallback_paths": []},
            "endpoint_url": f"/api/bus/in/{slug}",
        },
        "printer_selection": {"mode": "from_request", "path": "request.body.printer", "fixed_printer_name": "LINE-1-ZEBRA"},
        "labels": {
            "path": "request.body.labels",
            "item_as": "label",
            "required_fields": ["code"],
            "optional_fields": ["sku", "title", "qty", "sequence_no"],
        },
        "zpl": {
            "template": "^XA\n^CI28\n^FO30,30^A0N,30,30^FD{{label.title}}^FS\n^FO30,70^A0N,24,24^FDSKU: {{label.sku}}^FS\n^FO30,110^BXN,5,200^FD{{label.code}}^FS\n^FO30,300^A0N,24,24^FD#{{label.sequence_no}} / {{request.body.job_key}}^FS\n^XZ",
        },
        "print_mode": {"mode": "dry_run"},
        "response": {
            "type": "normalized_print_status",
            "status_code": 200,
            "body": {
                "success": True,
                "print_job_id": "{{print_job.id}}",
                "labels_count": "{{labels.length}}",
                "printer": "{{selected_printer.name}}",
                "status": "{{print_job.status}}",
            },
            "headers": {"Content-Type": "application/json"},
        },
    }


def _timeline_artifact_names(timeline: dict) -> set[str]:
    names: set[str] = set()
    for run in timeline.get("runs") or []:
        for artifact in run.get("artifacts") or []:
            names.add(artifact.get("name"))
        for step in run.get("steps") or []:
            for artifact in step.get("artifacts") or []:
                names.add(artifact.get("name"))
    return {name for name in names if name}


async def _dnp_chz_pattern_payload(client, connection_id: str, *, slug: str):
    parse = await client.post(
        "/api/integration-master/input/parse",
        json={
            "input_mode": "json",
            "scenario_key": "dnp_chz_code_pool",
            "sample": {
                "operation": "dnp_sinc_pull_codes",
                "sinc": "dnp_sinc_pull_codes",
                "order_id": 10271,
                "order_name": "26-0666/6938",
                "Number": "260666/6938",
            },
        },
    )
    assert parse.status_code == 200, parse.text
    parse_result = parse.json()
    return {
        "name": "DnP запрашивает пул кодов Честного знака",
        "slug": slug,
        "input_contract": {
            "name": "DnP запрашивает пул кодов Честного знака",
            "slug": slug,
            "input_mode": "json",
            "source_system": "dnp",
            "scenario_key": "dnp_chz_code_pool",
            "sample": parse_result["normalized_sample"],
            "fields": parse_result["fields"],
            "operation_key": {
                "type": "field",
                "field_path": "request.body.sinc",
                "value": "dnp_sinc_pull_codes",
                "fallback_paths": ["request.body.operation"],
                "matcher_preview": {
                    "mode": "any",
                    "rules": [
                        {"type": "body_path_equals", "path": "sinc", "value": "dnp_sinc_pull_codes"},
                        {"type": "body_path_equals", "path": "operation", "value": "dnp_sinc_pull_codes"},
                    ],
                },
            },
            "business_key": {"path": "request.body.order_name", "fallback_paths": ["request.body.Number"]},
            "endpoint_url": f"/api/bus/in/{slug}",
        },
        "find_order": {
            "type": "odata_query",
            "connection_id": connection_id,
            "connection_name": "1C CHZ OData ERP",
            "resource": "Document_ЗаказНаПроизводство2_2",
            "filter_mode": "raw",
            "filter_rule": {"field": "Number", "operator": "eq", "value_type": "variable", "value": "request.body.Number"},
            "filter": "Number eq '{{request.body.Number}}'",
            "select": ["Ref_Key", "Number", "Date", "Posted"],
            "top": 1,
            "orderby": None,
            "paginate": False,
            "save_as": "order",
            "required": True,
        },
        "read_products": {
            "type": "odata_object_query",
            "connection_id": connection_id,
            "connection_name": "1C CHZ OData ERP",
            "object_variable": "order",
            "key_field": "Ref_Key",
            "key_type": "guid",
            "base_resource": "Document_ЗаказНаПроизводство2_2",
            "nested_resource": "Продукция",
            "filter": None,
            "select": ["Номенклатура_Key", "Количество", "КоличествоУпаковок"],
            "top": 100,
            "paginate": False,
            "save_as": "products",
            "required": True,
            "overwrite": True,
        },
        "find_codes": {
            "type": "foreach_odata",
            "items": "products",
            "item_as": "product",
            "connection_id": connection_id,
            "connection_name": "1C CHZ OData ERP",
            "resource": "InformationRegister_ПулКодовМаркировкиСУЗ",
            "filter": "Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')",
            "select": DNP_CODE_SELECT,
            "top": 500,
            "paginate": True,
            "merge": "flatten",
            "save_as": "codes",
            "required": True,
            "limits": {"max_items": 100, "max_requests": 100, "max_result_rows": 10000},
            "test_limit": None,
            "overwrite": True,
        },
        "payload": {
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
                    "order_id": "{{request.body.order_id}}",
                    "odata_url": "http://172.16.3.19/erp_ptc/odata/standard.odata/InformationRegister_ПулКодовМаркировкиСУЗ",
                    "order_name": "{{request.body.order_name}}",
                    "onec_order_number": "{{order.Number}}",
                    "order_numbers_by_basis": {"{{order.Ref_Key}}": "{{order.Number}}"},
                },
            },
            "fields": [],
            "dynamic_entries": [],
            "overwrite": True,
        },
        "target": {
            "method": "POST",
            "url": "http://172.16.3.10/api/v2/integrations/omh/chz/codes/import",
            "headers": {"Content-Type": "application/json"},
            "body_source": "target_payload",
            "body_type": "json",
            "timeout_seconds": 30,
        },
        "response_to_caller": {"type": "fixed_success", "status_code": 200, "body": {"ok": True}, "headers": {"Content-Type": "application/json"}},
    }
