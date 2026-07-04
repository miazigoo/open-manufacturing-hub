from app.packages.manifest import PackageBackendManifest, PackageDocsManifest, PackageFrontendManifest, PackageManifest, PackageNavigationItem

manifest = PackageManifest(
    package_id="omh-package-auth",
    name="Auth Package",
    version="0.1.0",
    description="Optional login, users, sessions and recovery keys for OMH.",
    official=True,
    category="Security",
    capabilities=["auth", "users", "sessions", "frontend_pages", "package_settings"],
    backend=PackageBackendManifest(routers=["app.packages_auth.router:router"], modules=["app.packages_auth"]),
    frontend=PackageFrontendManifest(
        navigation=[
            PackageNavigationItem(group="Settings", title="Users", route="/users"),
            PackageNavigationItem(group="Settings", title="Auth", route="/auth-settings"),
        ]
    ),
    docs=PackageDocsManifest(readme="app.packages_auth.docs:README", quick_start="app.packages_auth.docs:QUICK_START"),
)
