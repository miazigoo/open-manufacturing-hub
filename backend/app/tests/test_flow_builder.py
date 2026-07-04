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
