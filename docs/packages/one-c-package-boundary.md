# 1C Package Boundary

`omh-package-onec` owns 1C-specific UI pages, OData explorer routes, XML inbound workbench routes, 1C scenarios, operation templates and visual flow-builder blocks.

When the package is disabled, OMH keeps existing data but hides navigation items and blocks package API routes with `PACKAGE_DISABLED`.

Core runtime endpoints stay available: integration bus inbound routes, events, queue, packages, exports and production checks.
