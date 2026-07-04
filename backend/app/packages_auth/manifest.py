from app.packages.manifest import PackageBackendManifest, PackageDocsManifest, PackageFrontendManifest, PackageFrontendPage, PackageManifest, PackageNavigationItem

manifest = PackageManifest(
    package_id="omh-package-auth",
    name="Auth Package",
    version="0.1.0",
    description="Optional users, sessions, login page and recovery keys for OMH.",
    official=True,
    category="Security",
    status="available",
    installable=True,
    capabilities=["auth", "users", "sessions", "frontend_pages", "package_settings"],
    backend=PackageBackendManifest(routers=["app.packages_auth.router:router"], modules=["app.packages_auth"]),
    frontend=PackageFrontendManifest(
        pages=[
            PackageFrontendPage(route="/login", title="Login", component="LoginPage"),
            PackageFrontendPage(route="/bootstrap", title="Create first user", component="BootstrapPage"),
            PackageFrontendPage(route="/users", title="Users", component="UsersPage"),
            PackageFrontendPage(route="/change-password", title="Change Password", component="ChangePasswordPage"),
            PackageFrontendPage(route="/auth-settings", title="Auth Settings", component="AuthSettingsPage"),
        ],
        navigation=[
            PackageNavigationItem(group="Settings", title="Users", route="/users"),
            PackageNavigationItem(group="Settings", title="Auth", route="/auth-settings"),
        ],
    ),
    docs=PackageDocsManifest(readme="app.packages_auth.docs:README", quick_start="app.packages_auth.docs:QUICK_START"),
)
