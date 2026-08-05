import pytest

pytestmark = pytest.mark.anyio


async def _create_flow(client, slug: str, steps: list[dict]) -> dict:
    builder = {
        "version": 1,
        "input": {"endpoint_slug": slug, "input_mode": "json", "response_mode": "sync_response", "processing_mode": "sync_inline"},
        "steps": steps,
    }
    response = await client.post(
        "/api/integration-flows",
        json={
            "name": slug,
            "slug": slug,
            "endpoint": {"input_mode": "json", "response_mode": "sync_response", "processing_mode": "sync_inline"},
            "builder_json": builder,
            "matcher_group_json": {"mode": "all", "rules": [{"type": "always"}]},
        },
    )
    assert response.status_code == 422 or response.status_code == 200, response.text
    assert response.status_code == 200, response.text
    return response.json()


async def _create_mock_connector(client, name: str, mock_body: dict | None = None) -> None:
    response = await client.post(
        "/api/connectors",
        json={
            "name": name,
            "connector_type": "rest",
            "direction": "target",
            "enabled": True,
            "config_json": {"method": "POST", "url": "http://target.local/receive", "mock_response_json": mock_body or {"ok": True}},
        },
    )
    assert response.status_code in (200, 201), response.text


async def _dispatch(client, slug: str, payload: dict) -> dict:
    response = await client.post(f"/api/bus/in/{slug}", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


async def _timeline_steps(client, event_id: str) -> list[dict]:
    timeline = await client.get(f"/api/events/{event_id}/timeline")
    assert timeline.status_code == 200, timeline.text
    return timeline.json()["runs"][0]["steps"]


async def test_run_if_skips_step(client):
    slug = "run-if-demo"
    await _create_flow(client, slug, [
        {"id": "read", "type": "read_variable", "path": "request.body.value", "save_as": "value"},
        {
            "id": "build",
            "type": "build_json",
            "template": {"echo": "{{value}}"},
            "save_as": "target_payload",
            "run_if": {"mode": "all", "rules": [{"type": "body_path_equals", "path": "request.body.flag", "value": "on"}]},
        },
        {"id": "respond", "type": "return_response", "body": {"ok": True}},
    ])

    result = await _dispatch(client, slug, {"value": "A", "flag": "off"})
    steps = await _timeline_steps(client, result["event_id"])
    build_step = next(step for step in steps if step["step_name"] == "build")
    assert build_step["status"] == "skipped"

    result = await _dispatch(client, slug, {"value": "A", "flag": "on"})
    steps = await _timeline_steps(client, result["event_id"])
    build_step = next(step for step in steps if step["step_name"] == "build")
    assert build_step["status"] == "success"


async def test_condition_matcher_group_skips_branch(client):
    slug = "condition-branch-demo"
    await _create_mock_connector(client, "Mock Target Branch")
    await _create_flow(client, slug, [
        {
            "id": "check",
            "type": "condition",
            "matcher_group": {"mode": "all", "rules": [{"type": "body_path_equals", "path": "request.body.pool_type", "value": "DNP"}]},
            "else": "skip",
            "skip_steps": ["send"],
        },
        {"id": "send", "type": "call_endpoint", "connector": "Mock Target Branch", "method": "POST", "path": "/codes", "body": {"pool": "{{request.body.pool_type}}"}, "save_response_as": "send_result"},
        {"id": "respond", "type": "return_response", "body": {"ok": True}},
    ])

    matched = await _dispatch(client, slug, {"pool_type": "DNP"})
    steps = await _timeline_steps(client, matched["event_id"])
    names = {step["step_name"]: step["status"] for step in steps}
    assert names.get("send") == "success"

    skipped = await _dispatch(client, slug, {"pool_type": "OTHER"})
    steps = await _timeline_steps(client, skipped["event_id"])
    names = {step["step_name"]: step["status"] for step in steps}
    assert "send" not in names
    assert names.get("check") == "success"


async def test_legacy_condition_expression_still_works(client):
    slug = "legacy-condition-demo"
    await _create_flow(client, slug, [
        {"id": "check", "type": "condition", "if": "request.body.a == 1", "else": "fail", "error_message": "a must be 1"},
        {"id": "respond", "type": "return_response", "body": {"ok": True}},
    ])
    ok = await _dispatch(client, slug, {"a": 1})
    steps = await _timeline_steps(client, ok["event_id"])
    assert next(step for step in steps if step["step_name"] == "check")["status"] == "success"

    failed = await _dispatch(client, slug, {"a": 2})
    event = await client.get(f"/api/events/{failed['event_id']}")
    assert event.json()["status"] == "failed"


async def test_extract_step_json_and_regex(client):
    slug = "extract-demo"
    await _create_flow(client, slug, [
        {
            "id": "parse",
            "type": "extract",
            "source": "request.body",
            "fields": [
                {"name": "order_no", "path": "order.number"},
                {"name": "amounts", "regex": r"total=(\d+)", "mode": "all"},
            ],
        },
        {"id": "respond", "type": "return_response", "body": {"order_no": "{{order_no}}", "amounts": "{{amounts}}"}},
    ])
    result = await _dispatch(client, slug, {"order": {"number": "260530/6543"}, "note": "total=10 total=25"})
    assert result["body"]["order_no"] == "260530/6543"
    assert result["body"]["amounts"] == ["10", "25"]


async def test_extract_missing_required_field_fails(client):
    slug = "extract-required-demo"
    await _create_flow(client, slug, [
        {"id": "parse", "type": "extract", "source": "request.body", "fields": [{"name": "needed", "path": "absent.path", "required": True}]},
        {"id": "respond", "type": "return_response", "body": {"ok": True}},
    ])
    result = await _dispatch(client, slug, {"x": 1})
    steps = await _timeline_steps(client, result["event_id"])
    parse_step = next(step for step in steps if step["step_name"] == "parse")
    assert parse_step["status"] == "failed"
    assert parse_step["error_code"] == "EXTRACT_FIELD_MISSING"


async def test_filter_array_by_key(client):
    slug = "filter-demo"
    await _create_flow(client, slug, [
        {
            "id": "filter",
            "type": "filter_array",
            "items": "request.body.rows",
            "where": {"mode": "all", "rules": [{"type": "body_path_starts_with", "path": "item.sku", "value": "A"}]},
            "save_as": "filtered",
        },
        {"id": "respond", "type": "return_response", "body": {"items": "{{filtered}}"}},
    ])
    result = await _dispatch(client, slug, {"rows": [{"sku": "A1"}, {"sku": "B1"}, {"sku": "A2"}]})
    assert [item["sku"] for item in result["body"]["items"]] == ["A1", "A2"]


async def test_foreach_call_endpoint_sends_each_item(client):
    slug = "foreach-send-demo"
    await _create_mock_connector(client, "Mock Target Foreach", {"accepted": True})
    await _create_flow(client, slug, [
        {
            "id": "send_each",
            "type": "foreach",
            "items": "request.body.codes",
            "item_as": "code_row",
            "save_as": "sent",
            "step": {
                "type": "call_endpoint",
                "connector": "Mock Target Foreach",
                "method": "POST",
                "path": "/codes",
                "body": {"code": "{{code_row.code}}"},
                "save_response_as": "send_result",
            },
        },
        {"id": "respond", "type": "return_response", "body": {"sent": "{{sent}}"}},
    ])
    result = await _dispatch(client, slug, {"codes": [{"code": "c1"}, {"code": "c2"}]})
    assert result["body"]["sent"] == [{"accepted": True}, {"accepted": True}]
    steps = await _timeline_steps(client, result["event_id"])
    send_step = next(step for step in steps if step["step_name"] == "send_each")
    assert send_step["status"] == "success"
    artifact_names = {artifact["name"] for artifact in send_step["artifacts"]}
    assert "foreach_input.json" in artifact_names


async def test_foreach_build_json_maps_items(client):
    slug = "foreach-build-demo"
    await _create_flow(client, slug, [
        {
            "id": "map_each",
            "type": "foreach",
            "items": "request.body.rows",
            "item_as": "row",
            "save_as": "mapped",
            "step": {"type": "build_json", "template": {"sku": "{{row.sku}}", "qty": "{{row.qty}}"}, "save_as": "mapped_row"},
        },
        {"id": "respond", "type": "return_response", "body": {"mapped": "{{mapped}}"}},
    ])
    result = await _dispatch(client, slug, {"rows": [{"sku": "A", "qty": 1}, {"sku": "B", "qty": 2}]})
    assert result["body"]["mapped"] == [{"sku": "A", "qty": 1}, {"sku": "B", "qty": 2}]


async def test_build_xml_step_and_invalid_template(client):
    slug = "build-xml-demo"
    await _create_flow(client, slug, [
        {"id": "xml", "type": "build_xml", "body_template": "<Response><Number>{{request.body.number}}</Number></Response>", "save_as": "xml_body"},
        {"id": "respond", "type": "return_response", "body": {"xml": "{{xml_body}}"}},
    ])
    result = await _dispatch(client, slug, {"number": "260530/6543"})
    assert result["body"]["xml"] == "<Response><Number>260530/6543</Number></Response>"

    slug2 = "build-xml-broken"
    await _create_flow(client, slug2, [
        {"id": "xml", "type": "build_xml", "body_template": "<Response><broken", "save_as": "xml_body"},
        {"id": "respond", "type": "return_response", "body": {"ok": True}},
    ])
    result = await _dispatch(client, slug2, {})
    steps = await _timeline_steps(client, result["event_id"])
    xml_step = next(step for step in steps if step["step_name"] == "xml")
    assert xml_step["status"] == "failed"
    assert xml_step["error_code"] == "XML_NOT_WELL_FORMED"


async def test_preview_simulates_logic_steps(client):
    builder = {
        "version": 1,
        "input": {"endpoint_slug": "preview-logic", "input_mode": "json", "response_mode": "sync_response"},
        "steps": [
            {"id": "check", "type": "condition", "matcher_group": {"mode": "all", "rules": [{"type": "body_path_equals", "path": "request.body.pool_type", "value": "DNP"}]}, "else": "skip", "skip_steps": ["send"]},
            {"id": "filter", "type": "filter_array", "items": "request.body.rows", "where": {"mode": "all", "rules": [{"type": "body_path_starts_with", "path": "item.sku", "value": "A"}]}, "save_as": "filtered"},
            {"id": "parse", "type": "extract", "source": "request.body", "fields": [{"name": "total", "regex": r"total=(\d+)"}]},
            {"id": "send", "type": "call_endpoint", "url": "http://target.local/x", "body": "{{filtered}}"},
            {"id": "xml", "type": "build_xml", "body_template": "<R><N>{{request.body.number}}</N></R>", "save_as": "xml_body"},
            {"id": "respond", "type": "return_response", "body": {"ok": True}},
        ],
    }
    response = await client.post(
        "/api/flow-builder/preview",
        json={"builder_json": builder, "sample_request": {"pool_type": "OTHER", "number": "N1", "note": "total=42", "rows": [{"sku": "A1"}, {"sku": "B1"}]}},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True, body.get("errors")
    by_id = {step["id"]: step for step in body["steps"]}
    assert by_id["send"]["status"] == "skipped"
    assert by_id["filter"]["result_preview"]["passed"] == 1
    assert by_id["parse"]["result_preview"]["total"] == "42"
    assert by_id["xml"]["result_preview"]["xml"] == "<R><N>N1</N></R>"
