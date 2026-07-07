# Monorepo Official Packages

Open Manufacturing Hub keeps official packages in the main repository until the Package SDK, frontend extension contract and release tooling are stable enough for external package repositories.

This is a build-time decision, not a runtime shortcut.

- OMH Core remains the integration runtime.
- Official package source code is shipped with the monorepo build.
- Packages are still optional at runtime and must be installed/enabled per OMH instance.
- Community packages may move to separate repositories after the SDK is stable.

## Current Official Packages

The current monorepo official packages are:

- `omh-package-onec`
- `omh-package-printer`
- `omh-package-auth`
- `omh-package-secrets`

Their backend manifests live under `backend/app/packages_*`. Auth frontend package entry files live under `frontend/src/packages/auth` and re-export the implementation from `frontend/src/features/auth`.

## Lifecycle Terms

`registered` means package code is known to the runtime or catalog. It does not mean the package is active for this OMH instance.

`available` means the package is released and can be installed from Plugin Store.

`installed` means an `InstalledPackage` database record exists for this OMH instance.

`enabled` means the installed package is active and its package-specific routes/pages can be used.

`disabled` means the package is installed but inactive.

`coming_soon` means the package is visible in Plugin Store but cannot be installed.

`in_development` means the package is being built and is locked by default.

`incompatible` means the package exists but cannot run on the current OMH Core version.

## Navigation And Route Rules

Package-specific operational navigation is shown only when the package is installed and enabled.

For example, `omh-package-onec` being registered in the monorepo does not show 1C cockpit, OData Master or 1C workbench as normal operational nav. These pages become normal navigation only after `omh-package-onec` is installed and enabled.

Direct package-specific pages are wrapped by `PackageGate`. The gate shows:

- install prompt for available but not installed packages;
- enable prompt for installed but disabled packages;
- coming soon / in development / incompatible states for locked packages;
- the real page only when the package is installed and enabled.

Backend package-specific routes are guarded with package state. Core APIs and Plugin Store remain available.

## Auth Package

`omh-package-auth` is optional. When not installed/enabled, OMH starts normally without login.

When Auth is installed and enabled:

- `/api/auth/state` stays public and reports whether login/bootstrap is required;
- if no users exist, the frontend shows bootstrap once;
- after the first user exists, the frontend shows login;
- created users receive recovery keys;
- enabled users can access the full UI;
- inbound integration endpoints keep their own endpoint authentication and are not blocked by UI auth.

## Auto Install

Production does not silently install official packages.

Use explicit configuration only when desired:

```text
OMH_AUTO_INSTALL_PACKAGES=omh-package-onec,omh-package-printer
```

Default is empty. Development environments may set it for convenience, but production should install packages intentionally from Plugin Store or package APIs.

## When Packages Can Move Out

Official packages can move to separate repositories after the following are stable:

- backend Package SDK;
- frontend extension/bundle contract;
- package signatures and provenance;
- compatibility checks;
- install/update/rollback semantics;
- CI checks equivalent to `make check-official-packages`.

Until then, monorepo official packages avoid missing frontend/backend code while preserving runtime modularity.
