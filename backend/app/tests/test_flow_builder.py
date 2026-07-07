import pytest

from app.json_builder.engine import build_json_from_template
from app.variables.paths import PathResolutionError, resolve_path
from app.variables.resolver import build_runtime_scope, render_template


async def test_path_resolver_and_template_renderer():
    data = {"request": {"body": {"items": [{"sku": "ABC"}], "codes": ["c1", "c2"]}}, "variables": {"contractor": {"Ref_Key": "uuid-1"}}}
    assert resolve_path(data, "request.body.items[0].sku") == "ABC"
    with pytest.raises(PathResolutionError):
        resolve_path(data, "request.body.items[2].sku")
    assert render_template("{{request.body.codes}}", data) == ["c1", "c2"]
    assert render_template("Contractor {{contractor.Ref_Key}}", data) == "Contractor uuid-1"


def test_json_builder_preserves_types():
    scope = build_runtime_scope(request_body={"pool_id": "POOL-001", "codes": ["c1"]}, variables={"contractor": {"Ref_Key": "uuid"}})
    result = build_json_from_template({"pool_id": "{{request.body.pool_id}}", "codes": "{{request.body.codes}}", "comment": "Pool {{request.body.pool_id}}"}, scope)
    assert result == {"pool_id": "POOL-001", "codes": ["c1"], "comment": "Pool POOL-001"}


def test_json_builder_renders_template_keys():
    scope = build_runtime_scope(request_body={}, variables={"order": {"Ref_Key": "order-guid", "Number": "260666/6938"}})
    result = build_json_from_template({"order_numbers_by_basis": {"{{order.Ref_Key}}": "{{order.Number}}"}}, scope)
    assert result == {"order_numbers_by_basis": {"order-guid": "260666/6938"}}


async def test_visual_flow_builder_preset_preview_compile_and_dispatch(client):
    installed = await client.post("/api/scenario-library/onec-post-two-odata-to-endpoint/install")
    assert installed.status_code == 200, installed.text
    flow = installed.json()
    assert flow["slug"] == "onec-pool-to-dnp"
    assert flow["builder_json"]["steps"][2]["type"] == "odata_query"
    assert flow["compiled_workflow_id"]

    preview = await client.post(
        "/api/flow-builder/preview",
        json={"builder_json": flow["builder_json"], "sample_request": flow["test_payload_json"]},
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    assert preview_body["valid"] is True
    assert preview_body["final_payload_preview"]["contractor_uuid"] == "contractor-uuid-001"
    assert preview_body["target_request_preview"]["body"]["product_uuid"] == "product-uuid-abc-123"

    compiled = await client.post(f"/api/flow-builder/flows/{flow['id']}/compile")
    assert compiled.status_code == 200, compiled.text
    assert compiled.json()["steps_json"][2]["name"] == "get_contractor"
    assert compiled.json()["steps_json"][2]["handler"] == "flow_odata_query"

    sent = await client.post("/api/bus/in/onec-pool-to-dnp", json=flow["test_payload_json"])
    assert sent.status_code == 200, sent.text
    response = sent.json()
    assert response["body"]["external_document_id"] == "DNP-POOL-001"

    timeline = await client.get(f"/api/events/{response['event_id']}/timeline")
    assert timeline.status_code == 200
    steps = timeline.json()["runs"][0]["steps"]
    names = [step["step_name"] for step in steps]
    assert "get_contractor" in names
    assert "get_product" in names
    assert "build_payload" in names
    build_step = next(step for step in steps if step["step_name"] == "build_payload")
    artifact_names = {artifact["name"] for artifact in build_step["artifacts"]}
    assert "json_builder_result.json" in artifact_names
    send_step = next(step for step in steps if step["step_name"] == "send_to_dnp")
    outgoing = next(artifact for artifact in send_step["artifacts"] if artifact["name"] == "outgoing_request.json")
    assert outgoing["content_json"]["body"]["contractor_uuid"] == "contractor-uuid-001"


async def test_flow_builder_odata_chaining_selects_fields_and_ignores_empty_filters(client):
    builder = {
        "version": 1,
        "input": {"endpoint_slug": "odata-chain", "input_mode": "json", "response_mode": "sync_response"},
        "steps": [
            {
                "id": "get_contractor",
                "type": "odata_query",
                "name": "Find contractor",
                "connection": "Demo 1C ERP",
                "resource": "Catalog_Контрагенты",
                "filter_builder": [{"field": "ИНН", "operator": "eq", "value": "{{request.body.inn}}"}],
                "select": ["Ref_Key", "Description", "ИНН"],
                "top": 1,
                "save_as": "contractor",
                "required": True,
                "mock_items": [{"Ref_Key": "contractor-001", "Description": "Demo contractor", "ИНН": "7707083893", "Unused": "must-not-be-read"}],
            },
            {
                "id": "get_last_order",
                "type": "odata_query",
                "name": "Find latest order",
                "connection": "Demo 1C ERP",
                "resource": "Document_ЗаказКлиента",
                "filter_builder": [
                    {"field": "Контрагент_Key", "operator": "eq", "value": "{{contractor.Ref_Key}}"},
                    {"field": "", "operator": "eq", "value": ""},
                ],
                "select": ["Ref_Key", "Number", "Date"],
                "orderby": "Date desc",
                "top": 1,
                "save_as": "last_order",
                "required": True,
                "mock_items": [{"Ref_Key": "order-001", "Number": "SO-1001", "Date": "2026-07-05T10:00:00"}],
            },
            {
                "id": "build_payload",
                "type": "build_json",
                "name": "Build target",
                "save_as": "target_payload",
                "template": {
                    "contractor_uuid": "{{contractor.Ref_Key}}",
                    "contractor_name": "{{steps.get_contractor.first.Description}}",
                    "last_order_uuid": "{{last_order.Ref_Key}}",
                    "last_order_number": "{{last_order.Number}}",
                },
            },
        ],
    }

    response = await client.post("/api/flow-builder/preview", json={"builder_json": builder, "sample_request": {"inn": "7707083893"}})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["steps"][1]["request_preview"]["query"]["$filter"] == "Контрагент_Key eq 'contractor-001'"
    assert body["steps"][1]["request_preview"]["query"]["$select"] == "Ref_Key,Number,Date"
    assert body["steps"][1]["request_preview"]["query"]["$orderby"] == "Date desc"
    assert body["final_payload_preview"] == {
        "contractor_uuid": "contractor-001",
        "contractor_name": "Demo contractor",
        "last_order_uuid": "order-001",
        "last_order_number": "SO-1001",
    }


async def test_flow_builder_return_response_preview_supports_xml_without_target_warning(client):
    builder = {
        "version": 1,
        "input": {"endpoint_slug": "lookup-order-products", "input_mode": "json", "response_mode": "sync_response"},
        "steps": [
            {
                "id": "get_order",
                "type": "odata_query",
                "name": "Find order",
                "connection": "Demo 1C ERP",
                "resource": "Document_ЗаказНаПроизводство2_2",
                "filter": "Number eq '{{request.body.Number}}'",
                "select": ["Ref_Key", "Number"],
                "top": 1,
                "save_as": "order",
                "required": True,
                "mock_items": [{"Ref_Key": "order-001", "Number": "260666/6938"}],
            },
            {
                "id": "return_response",
                "type": "return_response",
                "name": "Return XML",
                "response_body_type": "xml",
                "status_code": 200,
                "headers": {"Content-Type": "application/xml"},
                "body_template": "<Response><Order>{{order.Ref_Key}}</Order><Number>{{order.Number}}</Number></Response>",
            },
        ],
    }

    response = await client.post("/api/flow-builder/preview", json={"builder_json": builder, "sample_request": {"Number": "260666/6938"}})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["errors"] == []
    return_step = body["steps"][1]
    assert return_step["request_preview"]["response_body_type"] == "xml"
    assert return_step["result_preview"]["headers"]["Content-Type"] == "application/xml"
    assert return_step["result_preview"]["body"] == "<Response><Order>order-001</Order><Number>260666/6938</Number></Response>"
    assert all(warning["code"] != "TARGET_STEP_MISSING" for warning in body.get("warnings", []))
