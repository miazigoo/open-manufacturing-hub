from app.packages.manifest import PackageBackendManifest, PackageDocsManifest, PackageFrontendManifest, PackageManifest, PackageNavigationItem

manifest = PackageManifest(
    package_id="omh-package-secrets",
    name="Secrets Store Package",
    version="0.1.0",
    description="Secure configuration references, masked values and rotation tooling.",
    publisher="OMH",
    official=True,
    core_version_min="0.1.0",
    core_version_max="0.2.x",
    category="Security",
    capabilities=["secrets", "secure_config", "rotation", "frontend_pages", "production_checks"],
    backend=PackageBackendManifest(modules=["app.secrets"], routers=["app.secrets.router:router"]),
    frontend=PackageFrontendManifest(
        pages=[{"route": "/secrets", "title": "Secrets", "component": "SecretsPage"}],
        navigation=[PackageNavigationItem(group="Settings", title="Secrets", route="/secrets")],
    ),
    docs=PackageDocsManifest(readme="app.packages_secrets.docs:README", quick_start="app.packages_secrets.docs:QUICK_START"),
    extension_points=["Secure Config References", "Production Readiness Check"],
)
