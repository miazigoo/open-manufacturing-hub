# Package Runtime Boundaries

Packages register runtime capabilities in `package_runtime_capabilities`.

Capability rows answer operational questions such as which package owns a router, connector, navigation item, preset, execution step or builder block. Install and enable operations synchronize these rows; disable keeps them for diagnostics but marks them disabled.

Useful endpoints:

- `GET /api/packages/capabilities`
- `GET /api/packages/{package_id}/capabilities`
- `GET /api/packages/route-inventory`
- `GET /api/packages/compatibility-report`
- `GET /api/packages/{package_id}/check-upgrade`
- `POST /api/packages/{package_id}/mark-upgraded`
