from app.business_rules.engine import engine as rules_engine
from app.transforms.engine import engine as transform_engine


async def test_transform_registry_engine_and_api(client):
    listed = await client.get("/api/transforms")
    assert listed.status_code == 200, listed.text
    names = {item["name"] for item in listed.json()}
    assert {"trim", "uppercase", "replace", "date_format", "default_value", "hash_sha256"} <= names

    result = transform_engine.apply_chain("  abc  ", [{"name": "trim"}, {"name": "uppercase"}], {})
    assert result.success is True
    assert result.value == "ABC"
    assert [item.transform for item in result.trace] == ["trim", "uppercase"]

    replace = transform_engine.apply_chain("a b", [{"name": "replace", "args": {"old": " ", "new": "-"}}], {})
    assert replace.value == "a-b"
    date = transform_engine.apply_chain("2026-07-04T10:30:00Z", [{"name": "date_format", "args": {"format": "%Y%m%d"}}], {})
    assert date.value == "20260704"
    default = transform_engine.apply_chain("", [{"name": "default_value", "args": {"default": "fallback"}}], {})
    assert default.value == "fallback"
    unknown = transform_engine.apply_chain("x", [{"name": "missing_transform"}], {})
    assert unknown.success is False
    assert unknown.error_code == "TRANSFORM_NOT_FOUND"

    api = await client.post("/api/transforms/test", json={"value": "  abc  ", "chain": [{"name": "trim"}, {"name": "uppercase"}]})
    assert api.status_code == 200, api.text
    assert api.json()["result"] == "ABC"


async def test_business_rules_engine_and_api(client):
    rule_set = {
        "mode": "first_match",
        "rules": [
            {"name": "DNP", "if": {"path": "request.body.pool_type", "operator": "eq", "value": "DNP"}, "then": [{"action": "set_variable", "path": "variables.target_service", "value": "DNP Service"}, {"action": "set_target_system", "value": "DNP Service"}]},
            {"name": "Unknown", "if": {"operator": "always"}, "then": [{"action": "fail", "error_code": "UNKNOWN_POOL", "message": "Unknown {{request.body.pool_type}}"}]},
        ],
    }
    result = rules_engine.evaluate(rule_set, {"payload": {"pool_type": "DNP"}, "variables": {}})
    assert result.success is True
    assert result.matched_rules == ["DNP"]
    assert result.variables["target_service"] == "DNP Service"
    assert result.target_system == "DNP Service"

    failed = rules_engine.evaluate(rule_set, {"payload": {"pool_type": "OTHER"}, "variables": {}})
    assert failed.success is False
    assert failed.error_code == "UNKNOWN_POOL"
    assert failed.error_message == "Unknown OTHER"

    exists = rules_engine.evaluate({"mode": "all_matches", "rules": [{"name": "exists", "if": {"path": "request.body.inn", "operator": "exists"}, "then": [{"action": "set_operation", "value": "resolve"}]}, {"name": "amount", "if": {"path": "request.body.amount", "operator": "gt", "value": 0}, "then": [{"action": "set_route", "value": "positive"}]}]}, {"payload": {"inn": "123", "amount": 5}, "variables": {}})
    assert exists.operation == "resolve"
    assert exists.route == "positive"
    assert exists.matched_rules == ["exists", "amount"]

    created = await client.post("/api/business-rules", json={"name": "API rules", "rules_json": rule_set})
    assert created.status_code == 200, created.text
    tested = await client.post(f"/api/business-rules/{created.json()['id']}/test", json={"payload": {"pool_type": "DNP"}})
    assert tested.status_code == 200, tested.text
    assert tested.json()["matched_rules"] == ["DNP"]


async def test_apply_transforms_and_evaluate_rules_steps(client):
    workflow = await client.post(
        "/api/workflows",
        json={
            "name": "Transform rules workflow",
            "event_type": "TransformRulesEvent",
            "steps_json": [
                {"name": "receive"},
                {"name": "normalize", "handler": "apply_transforms", "config": {"step_id": "normalize", "chains": [{"source": "request.body.inn", "target": "variables.normalized_inn", "transforms": [{"name": "trim"}, {"name": "remove_spaces"}]}, {"source": "request.body.product_code", "target": "payload.product_code", "transforms": [{"name": "trim"}, {"name": "uppercase"}]}]}},
                {"name": "rules", "handler": "evaluate_rules", "config": {"step_id": "rules", "rules": [{"name": "good", "if": {"path": "request.body.product_code", "operator": "eq", "value": "ABC-123"}, "then": [{"action": "set_variable", "path": "variables.target_service", "value": "DNP Service"}]}]}},
            ],
            "validation_json": {"required_fields": []},
        },
    )
    assert workflow.status_code == 200, workflow.text
    event = await client.post("/api/events", json={"source_system": "1C", "target_system": "API", "event_type": "TransformRulesEvent", "entity_type": "Pool", "entity_id": "1", "payload": {"inn": " 12 3 ", "product_code": " abc-123 "}})
    assert event.status_code == 200, event.text
    timeline = await client.get(f"/api/events/{event.json()['id']}/timeline")
    assert timeline.status_code == 200, timeline.text
    steps = timeline.json()["runs"][0]["steps"]
    normalize = next(step for step in steps if step["step_name"] == "normalize")
    assert normalize["status"] == "success"
    assert "transform_trace.json" in {artifact["name"] for artifact in normalize["artifacts"]}
    rules = next(step for step in steps if step["step_name"] == "rules")
    assert rules["status"] == "success"
    assert "business_rules_trace.json" in {artifact["name"] for artifact in rules["artifacts"]}


async def test_flow_builder_transform_rule_compile_and_resolver_input_transforms(client):
    resolver = await client.post(
        "/api/resolvers",
        json={"name": "Normalized INN Resolver", "resolver_code": "normalized_inn_resolver", "object_type": "Customer", "strategy": "static_map", "input_schema_json": {"anyOf": ["inn"]}, "config_json": {"entries": [{"match": {"inn": "1234567890"}, "object": {"uuid": "cust-normalized", "inn": "1234567890"}}]}, "cache_enabled": False},
    )
    assert resolver.status_code == 200, resolver.text
    builder = {
        "version": 1,
        "input": {"endpoint_slug": "smart", "input_mode": "json", "response_mode": "proxy_response"},
        "steps": [
            {"id": "normalize", "type": "apply_transforms", "name": "Normalize", "chains": [{"source": "request.body.pool_type", "target": "payload.pool_type", "transforms": [{"name": "trim"}, {"name": "uppercase"}]}]},
            {"id": "rules", "type": "evaluate_rules", "name": "Rules", "rules": [{"name": "DNP", "if": {"path": "request.body.pool_type", "operator": "eq", "value": "DNP"}, "then": [{"action": "set_variable", "path": "variables.target_service", "value": "DNP Service"}]}]},
            {"id": "resolve", "type": "resolve_object", "name": "Resolve", "resolver": "normalized_inn_resolver", "save_as": "customer", "input": {"inn": {"source": "request.body.inn", "transforms": [{"name": "trim"}, {"name": "remove_spaces"}]}}},
            {"id": "send", "type": "call_endpoint", "name": "Send", "connector": "Mock WMS", "path": "/", "body": "{{customer}}"},
        ],
    }
    preview = await client.post("/api/flow-builder/preview", json={"builder_json": builder, "sample_request": {"pool_type": " dnp ", "inn": " 123 456 7890 "}})
    assert preview.status_code == 200, preview.text
    assert preview.json()["valid"] is True
    resolve_step = next(step for step in preview.json()["steps"] if step["id"] == "resolve")
    assert resolve_step["request_preview"]["input"]["inn"] == "1234567890"

    compiled = await client.post("/api/flow-builder/compile", json={"builder_json": builder})
    assert compiled.status_code == 200, compiled.text
    handlers = [step["handler"] for step in compiled.json()["steps_json"] if "handler" in step]
    assert "apply_transforms" in handlers
    assert "evaluate_rules" in handlers
