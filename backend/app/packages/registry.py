from __future__ import annotations

from app.core.errors import NotFoundError
from app.packages.manifest import PackageManifest


class PackageRegistry:
    def __init__(self) -> None:
        self._manifests: dict[str, PackageManifest] = {}

    def register_manifest(self, manifest: PackageManifest) -> None:
        self._manifests[manifest.package_id] = manifest

    def list_packages(self) -> list[PackageManifest]:
        return sorted(self._manifests.values(), key=lambda item: (not item.official, item.category, item.name))

    def get(self, package_id: str) -> PackageManifest:
        try:
            return self._manifests[package_id]
        except KeyError as exc:
            raise NotFoundError(f"Package {package_id} not found") from exc

    def is_registered(self, package_id: str) -> bool:
        return package_id in self._manifests


package_registry = PackageRegistry()


def register_builtin_packages() -> None:
    from app.packages_onec.manifest import manifest as onec_manifest
    from app.packages_printer.manifest import manifest as printer_manifest
    from app.packages_auth.manifest import manifest as auth_manifest
    from app.packages_secrets.manifest import manifest as secrets_manifest

    package_registry.register_manifest(onec_manifest)
    package_registry.register_manifest(printer_manifest)
    package_registry.register_manifest(auth_manifest)
    package_registry.register_manifest(secrets_manifest)


register_builtin_packages()
