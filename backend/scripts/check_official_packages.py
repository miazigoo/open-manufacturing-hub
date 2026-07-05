from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = REPO_ROOT / "backend" / "app" / "plugin_store" / "catalog.json"
REQUIRED_OFFICIAL_PACKAGES = {
    "omh-package-onec": {
        "backend_manifest": "backend/app/packages_onec/manifest.py",
    },
    "omh-package-printer": {
        "backend_manifest": "backend/app/packages_printer/manifest.py",
    },
    "omh-package-auth": {
        "backend_manifest": "backend/app/packages_auth/manifest.py",
        "frontend_entries": [
            "frontend/src/packages/auth/AuthGate.tsx",
            "frontend/src/packages/auth/LoginPage.tsx",
            "frontend/src/packages/auth/BootstrapPage.tsx",
            "frontend/src/packages/auth/UsersPage.tsx",
            "frontend/src/packages/auth/ChangePasswordPage.tsx",
            "frontend/src/packages/auth/AuthSettingsPage.tsx",
            "frontend/src/packages/auth/RecoveryKeysModal.tsx",
            "frontend/src/packages/auth/UserMenu.tsx",
            "frontend/src/packages/auth/api.ts",
            "frontend/src/packages/auth/types.ts",
        ],
    },
    "omh-package-secrets": {
        "backend_manifest": "backend/app/packages_secrets/manifest.py",
    },
    "omh-package-training": {
        "backend_manifest": "backend/app/packages_training/manifest.py",
        "frontend_entries": [
            "frontend/src/pages/TrainingPage.tsx",
            "frontend/src/api/training.ts",
        ],
    },
}


def main() -> int:
    errors: list[str] = []
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    catalog_by_id = {str(item.get("package_id")): item for item in catalog}

    for package_id, spec in REQUIRED_OFFICIAL_PACKAGES.items():
        if package_id not in catalog_by_id:
            errors.append(f"{package_id}: missing from plugin_store/catalog.json")
        manifest_path = REPO_ROOT / spec["backend_manifest"]
        if not manifest_path.exists():
            errors.append(f"{package_id}: missing backend manifest {spec['backend_manifest']}")
        item = catalog_by_id.get(package_id)
        if item:
            if item.get("official") is not True:
                errors.append(f"{package_id}: official catalog flag must be true")
            if item.get("status") != "available":
                errors.append(f"{package_id}: official monorepo packages must be available, got {item.get('status')!r}")
            if item.get("installable") is not True:
                errors.append(f"{package_id}: official monorepo packages must be installable")
        for entry in spec.get("frontend_entries", []):
            if not (REPO_ROOT / entry).exists():
                errors.append(f"{package_id}: missing frontend entry {entry}")

    official_catalog_ids = {str(item["package_id"]) for item in catalog if item.get("official")}
    missing_specs = official_catalog_ids - set(REQUIRED_OFFICIAL_PACKAGES)
    if missing_specs:
        errors.append(f"official catalog packages missing check spec: {', '.join(sorted(missing_specs))}")

    if errors:
        print("Official package check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"Official package check OK: {len(REQUIRED_OFFICIAL_PACKAGES)} packages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
