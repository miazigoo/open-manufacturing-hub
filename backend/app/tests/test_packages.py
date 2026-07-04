import pytest
from pydantic import ValidationError

from app.connectors.registry import registry as connector_registry
from app.packages.compatibility import validate_compatibility
from app.packages.manifest import PackageManifest
from app.packages.registry import package_registry


async def test_package_manifest_and_compatibility_validation():
    manifest = PackageManifest(package_id="omh-package-test", name="Test Package", version="0.1.0", description="Test", core_version_min="0.1.0", core_version_max="0.2.x")
    assert manifest.package_id == "omh-package-test"
    assert validate_compatibility(manifest, "0.1.0") == []
    assert validate_compatibility(manifest, "0.3.0")
    with pytest.raises(ValidationError):
        PackageManifest(name="Broken", version="0.1.0", description="Missing package id")


async def test_package_registry_has_builtin_boundaries():
    ids = {manifest.package_id for manifest in package_registry.list_packages()}
    assert "omh-package-onec" in ids
    assert "omh-package-printer" in ids
    assert package_registry.get("omh-package-onec").backend.connectors[0].endswith("OneCConnector")
    assert connector_registry.get("onec").connector_type == "onec"


async def test_package_installer_lifecycle_navigation_and_plugin_store(client):
    available = await client.get("/api/packages/available")
    assert available.status_code == 200, available.text
    assert {item["manifest"]["package_id"] for item in available.json()} >= {"omh-package-onec", "omh-package-printer"}

    store = await client.get("/api/plugin-store/catalog")
    assert store.status_code == 200, store.text
    onec_store = next(item for item in store.json() if item["package_id"] == "omh-package-onec")
    assert onec_store["installed"] is False

    installed = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": True})
    assert installed.status_code == 200, installed.text
    body = installed.json()
    assert body["package"]["status"] == "enabled"
    assert any(item["action"] == "install_demo_data" for item in body["log"])

    second_install = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert second_install.status_code == 200, second_install.text
    assert second_install.json()["package"]["id"] == body["package"]["id"]

    nav = await client.get("/api/packages/navigation")
    assert nav.status_code == 200
    enabled_routes = {item["route"] for item in nav.json() if item["enabled"]}
    assert "/onec-workbench" in enabled_routes

    disabled = await client.post("/api/packages/omh-package-onec/disable")
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["enabled"] is False
    nav_after_disable = await client.get("/api/packages/navigation")
    onec_workbench = next(item for item in nav_after_disable.json() if item["route"] == "/onec-workbench")
    assert onec_workbench["enabled"] is False

    enabled = await client.post("/api/packages/omh-package-onec/enable")
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["enabled"] is True

    docs = await client.get("/api/packages/omh-package-onec/docs")
    assert docs.status_code == 200
    assert "1C Integration Package" in docs.json()["readme"]

    export = await client.get("/api/packages/export-config")
    assert export.status_code == 200
    assert export.json()["installed_packages"][0]["package_id"] == "omh-package-onec"

    store_after = await client.get("/api/plugin-store/catalog")
    onec_after = next(item for item in store_after.json() if item["package_id"] == "omh-package-onec")
    assert onec_after["installed"] is True
    assert onec_after["enabled"] is True


async def test_printer_package_install_and_demo_data(client):
    installed = await client.post("/api/packages/omh-package-printer/install", json={"install_demo_data": False})
    assert installed.status_code == 200, installed.text
    assert installed.json()["package"]["package_id"] == "omh-package-printer"
    demo = await client.post("/api/packages/omh-package-printer/install-demo-data")
    assert demo.status_code == 200, demo.text
    assert demo.json()["log"][0]["status"] == "ok"
