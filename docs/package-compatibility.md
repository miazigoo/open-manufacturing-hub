# Package Compatibility

Integration packages declare the OMH Core versions they support through `core_version_min` and `core_version_max` in the package manifest.

Rules:

- Core API must remain backward compatible for installed packages within the declared version range.
- Installation fails when the current core version is outside the declared range.
- Startup validation marks incompatible packages as `incompatible` and disables their package navigation metadata.
- Package upgrades must not delete user data: endpoints, routes, workflows, mappings, operation templates, resolvers, connectors and business rules remain user-owned.
- Disabling a package hides package-provided navigation where feasible, but MVP keeps existing backend routes available to avoid production outages.

Production update checklist:

1. Export `/api/packages/export-config` before updating.
2. Run migrations.
3. Check `/api/packages/installed` for `failed` or `incompatible` statuses.
4. Re-enable packages only after compatibility errors are resolved.
