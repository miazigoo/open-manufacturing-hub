import pytest


async def _create_connection(client, *, kind="rest_api", name="DNP API", url="https://dnp.example.local"):
    config = {"url": url, "method": "POST", "timeout_seconds": 20, "headers": {"X-Source": "omh-test"}}
    if kind == "onec_http_service":
        config = {"http_service_base_url": url, "auth_type": "none", "timeout_seconds": 20}
    response = await client.post(
        "/api/connection-center/profiles",
        json={"name": name, "kind": kind, "description": "test profile", "enabled": True, "config_json": config, "tags": ["test"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_create_rest_operation_dry_run_and_options(client):
    connection = await _create_connection(client)
    response = await client.post(
        "/api/operation-catalog/operations",
        json={
            "name": "DNP import CHZ codes",
            "code": "dnp_import_chz_codes_test",
            "kind": "rest_api_operation",
            "connection_profile_id": connection["connector_id"],
            "method": "POST",
            "path": "/api/v2/integrations/omh/chz/codes/import",
            "headers_json": {"Content-Type": "application/json"},
            "body_type": "json",
            "success_condition_json": {"mode": "all", "conditions": [{"type": "http_status_2xx"}]},
            "response_extractors_json": [{"name": "request_id", "path": "request_id", "required": False}],
            "sample_request_json": {"order_number": "SO-1", "codes": ["0101"]},
            "sample_response_json": {"success": True, "request_id": "REQ-1"},
            "timeout_seconds": 30,
            "tags_json": ["dnp", "chz"],
        },
    )
    assert response.status_code == 200, response.text
    operation = response.json()
    assert operation["final_url"] == "https://dnp.example.local/api/v2/integrations/omh/chz/codes/import"

    options = (await client.get("/api/operation-catalog/options/rest")).json()
    assert [item["code"] for item in options] == ["dnp_import_chz_codes_test"]

    dry_run = await client.post(f"/api/operation-catalog/operations/{operation['id']}/test", json={"dry_run": True})
    assert dry_run.status_code == 200, dry_run.text
    body = dry_run.json()
    assert body["success"] is True
    assert body["dry_run"] is True
    assert body["request"]["final_url"].endswith("/chz/codes/import")
    assert body["request"]["body_preview"] == {"order_number": "SO-1", "codes": ["0101"]}


@pytest.mark.asyncio
async def test_mocked_real_request_success_conditions_and_extractors(client):
    connection = await _create_connection(client)
    created = await client.post(
        "/api/operation-catalog/operations",
        json={
            "name": "Website import order",
            "code": "website_import_order_test",
            "kind": "rest_api_operation",
            "connection_profile_id": connection["connector_id"],
            "method": "POST",
            "path": "/orders/import",
            "headers_json": {"Content-Type": "application/json"},
            "body_type": "json",
            "success_condition_json": {"mode": "all", "conditions": [{"type": "http_status_equals", "status": 202}, {"type": "json_path_equals", "path": "accepted", "value": True}, {"type": "json_path_exists", "path": "external_id"}]},
            "response_extractors_json": [{"name": "external_id", "path": "external_id", "required": True}],
            "sample_request_json": {"order_number": "SO-2"},
            "sample_response_json": {"accepted": True, "external_id": "SITE-2"},
        },
    )
    assert created.status_code == 200, created.text
    operation_id = created.json()["id"]

    response = await client.post(
        f"/api/operation-catalog/operations/{operation_id}/test",
        json={"dry_run": False, "confirm_real_request": True, "mock_response": True, "http_status": 202},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["http_status"] == 202
    assert body["success_condition_result"]["success"] is True
    assert body["extracted"] == {"external_id": "SITE-2"}


@pytest.mark.asyncio
async def test_missing_required_extractor_fails(client):
    connection = await _create_connection(client)
    created = await client.post(
        "/api/operation-catalog/operations",
        json={
            "name": "Broken extractor",
            "code": "broken_extractor_test",
            "kind": "rest_api_operation",
            "connection_profile_id": connection["connector_id"],
            "method": "POST",
            "path": "/orders/import",
            "body_type": "json",
            "success_condition_json": {"mode": "all", "conditions": [{"type": "http_status_2xx"}]},
            "response_extractors_json": [{"name": "external_id", "path": "external_id", "required": True}],
            "sample_response_json": {"accepted": True},
        },
    )
    assert created.status_code == 200, created.text
    response = await client.post(
        f"/api/operation-catalog/operations/{created.json()['id']}/test",
        json={"dry_run": False, "confirm_real_request": True, "mock_response": True},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is False
    assert "В ответе нет обязательного поля external_id." in body["errors"]


@pytest.mark.asyncio
async def test_onec_http_operation_and_disable_hides_from_options(client):
    connection = await _create_connection(client, kind="onec_http_service", name="1C ERP HTTP", url="https://onec.example.local/erp/hs/omh")
    created = await client.post(
        "/api/operation-catalog/operations",
        json={
            "name": "1C shipment fact",
            "code": "onec_shipment_fact_test",
            "kind": "onec_http_operation",
            "connection_profile_id": connection["connector_id"],
            "method": "POST",
            "path": "/shipment-facts",
            "headers_json": {"Content-Type": "application/json"},
            "body_type": "json",
            "success_condition_json": {"mode": "all", "conditions": [{"type": "http_status_2xx"}]},
            "sample_response_json": {"success": True},
        },
    )
    assert created.status_code == 200, created.text
    operation = created.json()
    assert operation["final_url"] == "https://onec.example.local/erp/hs/omh/shipment-facts"

    options = (await client.get("/api/operation-catalog/options/onec-http")).json()
    assert [item["code"] for item in options] == ["onec_shipment_fact_test"]

    disabled = await client.post(f"/api/operation-catalog/operations/{operation['id']}/disable")
    assert disabled.status_code == 200, disabled.text
    options_after = (await client.get("/api/operation-catalog/options/onec-http")).json()
    assert options_after == []


@pytest.mark.asyncio
async def test_manual_full_url_operation_keeps_legacy_endpoint_style(client):
    response = await client.post(
        "/api/operation-catalog/operations",
        json={
            "name": "Manual endpoint",
            "code": "manual_endpoint_test",
            "kind": "rest_api_operation",
            "connection_profile_id": None,
            "method": "POST",
            "full_url": "https://legacy.example.local/api/import",
            "headers_json": {"Content-Type": "application/json"},
            "body_type": "json",
            "success_condition_json": {"mode": "all", "conditions": [{"type": "always_success"}]},
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["final_url"] == "https://legacy.example.local/api/import"
