from app.packages.manifest import PackageManifest

manifest = PackageManifest(
    package_id="omh-package-training",
    name="Training Sandbox Package",
    version="0.1.0",
    description="Executable 1C/OData/API/printer training sandbox with mock systems, demo flows and runnable documentation examples.",
    publisher="OMH",
    official=True,
    core_version_min="0.1.0",
    core_version_max="0.2.x",
    category="Training",
    capabilities=[
        "training_sandbox",
        "mock_odata",
        "mock_api",
        "mock_printer",
        "demo_flows",
        "demo_test_cases",
        "docs_examples",
    ],
    backend={
        "modules": ["app.packages_training"],
        "routers": ["app.packages_training.router:router"],
    },
    frontend={
        "pages": [{"route": "/training", "title": "Training Sandbox", "component": "TrainingPage"}],
        "navigation": [{"group": "Build", "title": "Training Sandbox", "route": "/training"}],
    },
    docs={"readme": "app.packages_training.docs:README", "quick_start": "app.packages_training.docs:QUICK_START"},
    i18n={"namespaces": ["training"], "locales": {"ru": "i18n/ru/training.json", "en": "i18n/en/training.json", "zh": "i18n/zh/training.json"}},
    extension_points=["Package Store", "Mock OData", "Training Examples", "Test Console", "OData Explorer"],
    dependencies=[
        {"package_id": "omh-package-onec", "optional": True, "reason": "Enables the full 1C OData Explorer UI for training connections."},
        {"package_id": "omh-package-printer", "optional": True, "reason": "Lets users compare the mock printer with production printer tooling."},
    ],
)

