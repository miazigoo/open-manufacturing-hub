from __future__ import annotations

import pytest


pytestmark = pytest.mark.asyncio


async def test_connection_center_projects_legacy_connectors_and_tests_mock_odata(client):
    created = await client.post(
        "/api/connectors",
        json={
            "name": "Legacy ERP OData",
            "connector_type": "onec",
            "direction": "bidirectional",
            "enabled": True,
            "config_json": {
                "base_url": "http://training.local/odata/standard.odata",
                "auth": {"type": "none"},
                "odata": {"enabled": True, "default_page_size": 10, "max_pages": 1},
                "mock_odata": {"Catalog_Test": [{"Ref_Key": "1", "Description": "Тест"}]},
            },
        },
    )
    assert created.status_code == 200, created.text

    profiles = (await client.get("/api/connection-center/profiles")).json()
    profile = next(item for item in profiles if item["name"] == "Legacy ERP OData")
    assert profile["kind"] == "onec_odata"
    assert profile["id"].startswith("onec_odata:")

    tested = await client.post(f"/api/connection-center/profiles/{profile['id']}/test", json={"resource": "$metadata"})
    assert tested.status_code == 200, tested.text
    body = tested.json()
    assert body["success"] is True
    assert "metadata" in body["message"].lower()

    options = await client.get("/api/connection-center/options/odata")
    assert options.status_code == 200, options.text
    option = next(item for item in options.json() if item["label"] == "Legacy ERP OData")
    assert option["id"] == created.json()["id"]
    assert option["profile_id"] == profile["id"]


async def test_connection_center_create_profiles_mask_secrets_and_filter_disabled(client, tmp_path):
    odata = await client.post(
        "/api/connection-center/profiles",
        json={
            "name": "ERP OData Secret",
            "kind": "onec_odata",
            "config_json": {
                "base_url": "http://erp.local/odata/standard.odata",
                "auth_type": "basic",
                "username": "Администратор",
                "password": "raw-password",
            },
            "tags": ["erp"],
        },
    )
    assert odata.status_code == 200, odata.text
    odata_body = odata.json()
    assert odata_body["config_json"]["auth"]["password"] == "***"
    assert any("auth.password" in warning for warning in odata_body["warnings"])

    rest = await client.post(
        "/api/connection-center/profiles",
        json={"name": "DNP API", "kind": "rest_api", "config_json": {"url": "https://dnp.example/api/import", "method": "POST", "headers": {"Authorization": "Bearer raw"}}},
    )
    assert rest.status_code == 200, rest.text
    assert rest.json()["config_json"]["headers"]["Authorization"] == "***"

    onec_http = await client.post(
        "/api/connection-center/profiles",
        json={"name": "1C HTTP Service", "kind": "onec_http_service", "config_json": {"http_service_base_url": "http://onec.local/hs/omh", "auth_type": "none"}},
    )
    assert onec_http.status_code == 200, onec_http.text
    onec_test = await client.post(f"/api/connection-center/profiles/{onec_http.json()['id']}/test", json={})
    assert onec_test.status_code == 200, onec_test.text
    assert onec_test.json()["status"] == "configured"

    printer = await client.post(
        "/api/connection-center/profiles",
        json={"name": "Line Printer", "kind": "printer", "config_json": {"host": "127.0.0.1", "port": 9100, "dpi": 203, "printer_name": "LINE-1"}},
    )
    assert printer.status_code == 200, printer.text
    printer_test = await client.post(f"/api/connection-center/profiles/{printer.json()['id']}/test", json={})
    assert printer_test.status_code == 200, printer_test.text
    assert printer_test.json()["success"] is True
    assert printer_test.json()["dry_run"] is True

    smb = await client.post(
        "/api/connection-center/profiles",
        json={"name": "Laser SMB", "kind": "smb_share", "config_json": {"unc_path": "\\\\172.16.8.133\\DataMatrixCodes", "username": "guest", "password": "raw-smb"}},
    )
    assert smb.status_code == 200, smb.text
    smb_test = await client.post(f"/api/connection-center/profiles/{smb.json()['id']}/test", json={})
    assert smb_test.status_code == 200, smb_test.text
    assert smb_test.json()["success"] is True

    local_dir = await client.post(
        "/api/connection-center/profiles",
        json={"name": "Local Outbox", "kind": "local_directory", "config_json": {"path": str(tmp_path), "allow_overwrite": True}},
    )
    assert local_dir.status_code == 200, local_dir.text
    local_test = await client.post(f"/api/connection-center/profiles/{local_dir.json()['id']}/test", json={"confirm_write": True})
    assert local_test.status_code == 200, local_test.text
    assert local_test.json()["success"] is True

    rest_options = (await client.get("/api/connection-center/options/rest")).json()
    assert any(item["label"] == "DNP API" for item in rest_options)
    disabled = await client.post(f"/api/connection-center/profiles/{rest.json()['id']}/disable")
    assert disabled.status_code == 200, disabled.text
    rest_options_after_disable = (await client.get("/api/connection-center/options/rest")).json()
    assert all(item["label"] != "DNP API" for item in rest_options_after_disable)

    bundle = await client.get("/api/connection-center/options")
    assert bundle.status_code == 200, bundle.text
    assert "by_kind" in bundle.json()
    assert any(item["label"] == "Line Printer" for item in bundle.json()["by_kind"]["printer"])


async def test_connection_center_training_badges_from_training_connectors(client):
    installed = await client.post("/api/packages/omh-package-training/install", json={"install_demo_data": True})
    assert installed.status_code == 200, installed.text

    profiles = (await client.get("/api/connection-center/profiles")).json()
    names = {item["name"]: item for item in profiles}
    assert names["Training OData ERP"]["training"] is True
    assert names["Training OData ERP"]["kind"] == "onec_odata"
    assert names["Training OData WMS"]["training"] is True
    assert names["Training DNP API"]["kind"] == "rest_api"
    assert names["Training Printer"]["kind"] == "printer"
