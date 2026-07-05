from app.packages.manifest import PackageManifest

manifest = PackageManifest(
    package_id="omh-package-onec",
    name="1C Integration Package",
    version="0.1.0",
    description="1C ERP/WMS/OData/XML integration tools for OMH.",
    publisher="OMH",
    official=True,
    core_version_min="0.1.0",
    core_version_max="0.2.x",
    category="erp",
    capabilities=["connector", "odata", "odata_connection_catalog", "xml", "workbench", "scenario_library", "operation_templates", "frontend_pages", "visual_flow_builder"],
    backend={
        "modules": ["app.packages_onec"],
        "routers": ["app.packages_onec.router:router", "app.onec_workbench.router:router", "app.odata_connections.router:router", "app.odata_explorer.router:router", "app.xml_tools.router:router", "app.onec_scenarios.router:router", "app.onec_templates.router:router"],
        "connectors": ["app.packages_onec.connector:OneCConnector"],
        "steps": ["app.execution.steps.odata_lookup:ODataLookupStep"],
    },
    frontend={
        "pages": [
            {"route": "/onec-workbench", "title": "1C Workbench", "component": "OneCWorkbenchPage"},
            {"route": "/odata-connections", "title": "OData Connections", "component": "ODataConnectionsPage"},
            {"route": "/odata-explorer", "title": "OData Explorer", "component": "ODataExplorerPage"},
            {"route": "/xml-tools", "title": "XML Tools", "component": "XmlToolsPage"},
            {"route": "/onec-quick-setup", "title": "1C Quick Setup", "component": "OneCQuickSetupPage"},
            {"route": "/onec-scenarios", "title": "1C Scenarios", "component": "OneCScenariosPage"},
        ],
        "navigation": [
            {"group": "Integration Packages", "title": "1C Workbench", "route": "/onec-workbench"},
            {"group": "Integration Packages", "title": "OData Connections", "route": "/odata-connections"},
            {"group": "Integration Packages", "title": "OData Explorer", "route": "/odata-explorer"},
            {"group": "Integration Packages", "title": "XML Tools", "route": "/xml-tools"},
            {"group": "Integration Packages", "title": "1C Quick Setup", "route": "/onec-quick-setup"},
            {"group": "Integration Packages", "title": "1C Scenarios", "route": "/onec-scenarios"},
        ],
    },
    presets={"scenarios": "app.scenario_library.presets:SCENARIOS", "flow": "app.integration_flows.presets:TWO_ODATA_TO_ENDPOINT_PRESET"},
    docs={"readme": "app.packages_onec.docs:README", "quick_start": "app.packages_onec.docs:QUICK_START"},
    i18n={"namespaces": ["onec"], "locales": {"ru": "i18n/ru/onec.json", "en": "i18n/en/onec.json", "zh": "i18n/zh/onec.json"}},
    extension_points=["Connector SDK", "Execution Step SDK", "Frontend Navigation metadata", "Scenario Preset Installer", "Operation Template Installer", "Mapping Preset Installer"],
)
