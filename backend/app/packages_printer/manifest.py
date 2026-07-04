from app.packages.manifest import PackageManifest

manifest = PackageManifest(
    package_id="omh-package-printer",
    name="Printer Integration Package",
    version="0.1.0",
    description="ZPL printer integration, print jobs and production print timeline tooling.",
    publisher="OMH",
    official=True,
    core_version_min="0.1.0",
    core_version_max="0.2.x",
    category="hardware",
    capabilities=["connector", "printing", "frontend_pages", "scenario_library", "health_checks"],
    backend={
        "modules": ["app.packages_printer"],
        "routers": ["app.packages_printer.router:router", "app.printing.router:router"],
        "connectors": ["app.packages_printer.connector:ZPLPrinterConnector"],
        "steps": ["app.execution.steps.call_print_operation:CallPrintOperationStep"],
    },
    frontend={
        "pages": [{"route": "/printing", "title": "Printing", "component": "PrintingPage"}],
        "navigation": [{"group": "Integration Packages", "title": "Printing", "route": "/printing"}],
    },
    presets={"scenarios": "app.scenario_library.presets:SCENARIOS"},
    docs={"readme": "docs/printing.md", "quick_start": "docs/printing-quick-start.md"},
    extension_points=["Connector SDK", "Execution Step SDK", "Frontend Navigation metadata", "Scenario Preset Installer"],
)
