import pytest
from pathlib import Path
import subprocess
import sys
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
    assert {item["manifest"]["package_id"] for item in available.json()} >= {"omh-package-onec", "omh-package-printer", "omh-package-auth", "omh-package-secrets", "omh-package-training", "omh-package-sap"}
    onec_available = next(item for item in available.json() if item["manifest"]["package_id"] == "omh-package-onec")
    assert onec_available["registered"] is True
    assert onec_available["available"] is True
    assert onec_available["installed"] is False
    assert onec_available["enabled"] is False
    sap_available = next(item for item in available.json() if item["manifest"]["package_id"] == "omh-package-sap")
    assert sap_available["registered"] is True
    assert sap_available["available"] is False
    assert sap_available["status"] == "coming_soon"
    assert sap_available["manifest"]["installable"] is False
    assert "SAP OData connector" in sap_available["manifest"]["planned_capabilities"]

    store = await client.get("/api/plugin-store/catalog")
    assert store.status_code == 200, store.text
    onec_store = next(item for item in store.json() if item["package_id"] == "omh-package-onec")
    assert onec_store["registered"] is True
    assert onec_store["available"] is True
    assert onec_store["installed"] is False
    sap_store = next(item for item in store.json() if item["package_id"] == "omh-package-sap")
    assert sap_store["registered"] is True
    assert sap_store["available"] is False
    assert sap_store["status"] == "coming_soon"
    assert sap_store["installable"] is False

    sap_details = await client.get("/api/packages/omh-package-sap")
    assert sap_details.status_code == 200, sap_details.text
    assert sap_details.json()["manifest"]["expected_version"] == "0.2.0"

    blocked_install = await client.post("/api/packages/omh-package-sap/install", json={"install_demo_data": False})
    assert blocked_install.status_code == 400
    assert blocked_install.json()["error"] == "PACKAGE_NOT_INSTALLABLE"
    assert blocked_install.json()["package_id"] == "omh-package-sap"

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
    assert onec_after["status"] == "installed"


async def test_registered_package_routes_are_hidden_until_installed_in_ui_navigation(client):
    navigation = await client.get("/api/ui/navigation")
    assert navigation.status_code == 200, navigation.text
    onec_cockpit = next(item for item in navigation.json() if item["route"] == "/onec-cockpit")
    assert onec_cockpit["installed"] is False
    assert onec_cockpit["enabled"] is False

    installed = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert installed.status_code == 200, installed.text
    navigation_after_install = await client.get("/api/ui/navigation")
    onec_cockpit_after_install = next(item for item in navigation_after_install.json() if item["route"] == "/onec-cockpit")
    assert onec_cockpit_after_install["installed"] is True
    assert onec_cockpit_after_install["enabled"] is True


def test_official_package_check_script_passes():
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run([sys.executable, str(root / "scripts" / "check_official_packages.py")], cwd=root, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout


async def test_printer_package_install_and_demo_data(client):
    installed = await client.post("/api/packages/omh-package-printer/install", json={"install_demo_data": False})
    assert installed.status_code == 200, installed.text
    assert installed.json()["package"]["package_id"] == "omh-package-printer"
    demo = await client.post("/api/packages/omh-package-printer/install-demo-data")
    assert demo.status_code == 200, demo.text
    assert demo.json()["log"][0]["status"] == "ok"


async def test_package_capabilities_route_inventory_and_guards(client):
    blocked = await client.get("/api/odata-explorer/00000000-0000-0000-0000-000000000000/resources")
    assert blocked.status_code == 404
    assert blocked.json()["error"] == "PACKAGE_NOT_INSTALLED"

    installed = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert installed.status_code == 200, installed.text

    capabilities = await client.get("/api/packages/omh-package-onec/capabilities")
    assert capabilities.status_code == 200, capabilities.text
    capability_pairs = {(item["capability_type"], item["capability_code"]) for item in capabilities.json()}
    assert ("connector", "onec") in capability_pairs
    assert ("router", "odata_explorer") in capability_pairs
    assert ("navigation_item", "/onec-workbench") in capability_pairs

    route_inventory = await client.get("/api/packages/route-inventory")
    assert route_inventory.status_code == 200, route_inventory.text
    odata_route = next(item for item in route_inventory.json() if item["path"].startswith("/api/odata-explorer"))
    assert odata_route["package_id"] == "omh-package-onec"
    assert odata_route["guarded"] is True

    disabled = await client.post("/api/packages/omh-package-onec/disable")
    assert disabled.status_code == 200, disabled.text
    blocked_disabled = await client.get("/api/odata-explorer/00000000-0000-0000-0000-000000000000/resources")
    assert blocked_disabled.status_code == 403
    assert blocked_disabled.json()["error"] == "PACKAGE_DISABLED"
    disabled_capabilities = await client.get("/api/packages/omh-package-onec/capabilities")
    assert all(item["enabled"] is False for item in disabled_capabilities.json())


async def test_package_compatibility_dependencies_and_connector_catalog(client):
    connector_types = await client.get("/api/connectors/types")
    assert connector_types.status_code == 200
    initial_types = {item["connector_type"] for item in connector_types.json()}
    assert {"rest", "webhook", "mock_erp", "mock_wms"}.issubset(initial_types)
    assert "onec" not in initial_types

    report = await client.get("/api/packages/compatibility-report")
    assert report.status_code == 200
    printer = next(item for item in report.json()["packages"] if item["package_id"] == "omh-package-printer")
    assert any("OPTIONAL_PACKAGE_NOT_INSTALLED" in item for item in printer["warnings"])

    installed = await client.post("/api/packages/omh-package-onec/install", json={"install_demo_data": False})
    assert installed.status_code == 200, installed.text
    connector_types_after = await client.get("/api/connectors/types")
    assert "onec" in {item["connector_type"] for item in connector_types_after.json()}


async def test_required_package_dependency_blocks_install(client):
    manifest = PackageManifest(
        package_id="omh-package-dependent-test",
        name="Dependent Test",
        version="0.1.0",
        description="Requires missing package",
        dependencies=[{"package_id": "omh-package-missing", "optional": False}],
    )
    package_registry.register_manifest(manifest)
    try:
        response = await client.post("/api/packages/omh-package-dependent-test/install", json={"install_demo_data": False})
        assert response.status_code == 400
        assert "PACKAGE_DEPENDENCY_MISSING" in response.json()["detail"]
    finally:
        package_registry._manifests.pop("omh-package-dependent-test", None)
