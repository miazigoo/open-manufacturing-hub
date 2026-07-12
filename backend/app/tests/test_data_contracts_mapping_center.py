from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_create_data_contract(client):
    response = await client.post(
        "/api/data-contracts",
        json={
            "name": "Test Request",
            "code": "test_request",
            "kind": "operation_request",
            "schema_json": {"type": "object", "fields": [{"path": "payload.rows", "type": "array", "required": True}]},
            "example_json": {"payload": {"rows": [1]}},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == "test_request"
    assert data["fields"][0]["path"] == "payload.rows"


@pytest.mark.asyncio
async def test_render_mapping_variable_constant_template_dynamic_and_array(client):
    contract = (
        await client.post(
            "/api/data-contracts",
            json={
                "name": "Rendered Contract",
                "code": "rendered_contract",
                "kind": "operation_request",
                "schema_json": {
                    "type": "object",
                    "fields": [
                        {"path": "payload.rows", "type": "array", "required": True},
                        {"path": "payload.source", "type": "string", "required": True},
                        {"path": "payload.title", "type": "string", "required": True},
                        {"path": "payload.extra", "type": "object", "required": False},
                    ],
                },
            },
        )
    ).json()
    response = await client.post(
        "/api/mapping-center/preview",
        json={
            "target_contract_id": contract["id"],
            "source_context_json": {"codes": [{"code": "A"}], "order": {"Number": "SO-1"}, "dynamic": {"key": "warehouse", "value": "MAIN"}},
            "mapping_json": {
                "version": 1,
                "fields": [
                    {"target_path": "payload.rows", "source_type": "variable", "source": "codes", "preserve_type": True},
                    {"target_path": "payload.source", "source_type": "constant", "value": "OMH"},
                    {"target_path": "payload.title", "source_type": "template", "source": "Order {{order.Number}}"},
                ],
                "dynamic_entries": [{"object_path": "payload.extra", "key_source": "dynamic.key", "value_source": "dynamic.value"}],
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["payload"]["payload"]["rows"] == [{"code": "A"}]
    assert data["payload"]["payload"]["source"] == "OMH"
    assert data["payload"]["payload"]["title"] == "Order SO-1"
    assert data["payload"]["payload"]["extra"] == {"warehouse": "MAIN"}


@pytest.mark.asyncio
async def test_missing_variable_returns_structured_error(client):
    response = await client.post(
        "/api/mapping-center/preview",
        json={
            "source_context_json": {},
            "mapping_json": {"version": 1, "fields": [{"target_path": "payload.rows", "source_type": "variable", "source": "order.Number"}], "dynamic_entries": []},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["errors"][0]["error_code"] == "MAPPING_SOURCE_NOT_FOUND"
    assert "order.Number" in data["errors"][0]["message"]


@pytest.mark.asyncio
async def test_required_target_missing_and_type_mismatch(client):
    contract = (
        await client.post(
            "/api/data-contracts",
            json={
                "name": "Required Contract",
                "code": "required_contract",
                "kind": "operation_request",
                "schema_json": {"type": "object", "fields": [{"path": "payload.rows", "type": "array", "required": True}, {"path": "payload.qty", "type": "number", "required": False}]},
            },
        )
    ).json()
    missing = await client.post(
        "/api/mapping-center/preview",
        json={"target_contract_id": contract["id"], "source_context_json": {}, "mapping_json": {"version": 1, "fields": [], "dynamic_entries": []}},
    )
    assert missing.status_code == 200
    assert missing.json()["errors"][0]["error_code"] == "MAPPING_REQUIRED_FIELD_MISSING"

    mismatch = await client.post(
        "/api/mapping-center/validate",
        json={
            "target_contract_id": contract["id"],
            "source_context_json": {"qty": {"bad": True}, "rows": []},
            "mapping_json": {
                "version": 1,
                "fields": [
                    {"target_path": "payload.rows", "source_type": "variable", "source": "rows"},
                    {"target_path": "payload.qty", "source_type": "variable", "source": "qty"},
                ],
                "dynamic_entries": [],
            },
        },
    )
    assert mismatch.status_code == 200
    assert any(issue["error_code"] == "MAPPING_TYPE_MISMATCH" for issue in mismatch.json()["errors"])


@pytest.mark.asyncio
async def test_install_presets_dnp_mapping_and_operation_contract_reference(client):
    operation = await client.post(
        "/api/operation-catalog/operations",
        json={
            "name": "DNP import CHZ codes",
            "code": "dnp_import_chz_codes",
            "kind": "rest_api_operation",
            "enabled": True,
            "method": "POST",
            "full_url": "https://dnp.example/api/v2/integrations/omh/chz/codes/import",
            "headers_json": {"Content-Type": "application/json"},
            "body_type": "json",
            "response_body_type": "json",
            "success_condition_json": {"mode": "all", "conditions": [{"type": "http_status_2xx"}]},
            "response_extractors_json": [],
            "sample_request_json": {},
            "sample_response_json": {"success": True},
            "timeout_seconds": 30,
            "tags_json": ["dnp", "chz"],
        },
    )
    assert operation.status_code == 200

    install = await client.post("/api/mapping-center/install-presets")
    assert install.status_code == 200
    installed = install.json()
    assert any(item["code"] == "mapping_dnp_chz_codes_import" for item in installed["mappings"])
    assert "dnp_import_chz_codes" in installed["linked_operations"]

    mappings = (await client.get("/api/mapping-center/mappings")).json()
    dnp = next(item for item in mappings if item["code"] == "mapping_dnp_chz_codes_import")
    preview = await client.post("/api/mapping-center/preview", json={"mapping_profile_id": dnp["id"]})
    assert preview.status_code == 200
    payload = preview.json()["payload"]
    assert payload["payload"]["rows"] == [{"code": "0104600439937818215ABC", "nomenclature_key": "NOM-1"}]

    operation_after = (await client.get(f"/api/operation-catalog/operations/{operation.json()['id']}")).json()
    assert operation_after["request_contract_id"] == dnp["target_contract_id"]
