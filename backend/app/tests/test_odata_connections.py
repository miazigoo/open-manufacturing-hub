import pytest


pytestmark = pytest.mark.asyncio


async def test_odata_connection_catalog_lifecycle_and_package_guard(client):
    blocked = await client.get("/api/odata-connections")
    assert blocked.status_code == 404
    assert blocked.json()["error"] == "PACKAGE_NOT_INSTALLED"

    installed = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert installed.status_code == 200, installed.text

    payload = {
        "name": "OData ERP",
        "description": "ERP OData profile for integration flows",
        "base_url": "http://erp.local/base/odata/standard.odata",
        "auth_type": "basic",
        "username": "Администратор",
        "password": "123",
        "timeout_seconds": 10,
        "verify_ssl": False,
        "default_top": 50,
        "max_pages": 3,
        "tags": ["ERP", "contractors"],
    }
    created = await client.post("/api/odata-connections", json=payload)
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["name"] == "OData ERP"
    assert body["connector_id"] == body["id"]
    assert body["base_url"].endswith("/odata/standard.odata")
    assert body["config_json"]["auth"]["password"] == "***"
    assert body["default_top"] == 50

    options = await client.get("/api/odata-connections/options")
    assert options.status_code == 200, options.text
    assert options.json()[0]["label"] == "OData ERP"

    patched = await client.patch(f"/api/odata-connections/{body['id']}", json={"description": "Updated", "default_top": 25})
    assert patched.status_code == 200, patched.text
    patched_body = patched.json()
    assert patched_body["name"] == "OData ERP"
    assert patched_body["description"] == "Updated"
    assert patched_body["default_top"] == 25

    disabled = await client.patch(f"/api/odata-connections/{body['id']}", json={"enabled": False})
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["enabled"] is False

    removed = await client.delete(f"/api/odata-connections/{body['id']}")
    assert removed.status_code == 204
    listed = await client.get("/api/odata-connections")
    assert listed.status_code == 200
    assert listed.json() == []
