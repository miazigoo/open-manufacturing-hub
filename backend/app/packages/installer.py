from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import IntegrationPackageStatus
from app.core.errors import BadRequestError, NotFoundError
from app.packages.compatibility import validate_compatibility
from app.packages.models import InstalledPackage
from app.packages.registry import PackageRegistry, package_registry
from app.packages import repository


class PackageInstaller:
    def __init__(self, registry: PackageRegistry | None = None) -> None:
        self.registry = registry or package_registry

    async def install_package(self, session: AsyncSession, package_id: str, *, install_demo_data: bool = False) -> tuple[InstalledPackage, list[dict[str, Any]]]:
        manifest = self.registry.get(package_id)
        log = [_log("load_manifest", "ok", f"Loaded {manifest.name} {manifest.version}")]
        compatibility_errors = validate_compatibility(manifest)
        existing = await repository.get_installed(session, package_id)
        if compatibility_errors:
            package = existing or InstalledPackage(package_id=manifest.package_id, name=manifest.name, version=manifest.version, official=manifest.official, enabled=False, status=IntegrationPackageStatus.INCOMPATIBLE, manifest_json=manifest.to_json(), install_log_json=log, last_error="; ".join(compatibility_errors))
            if existing is None:
                session.add(package)
            else:
                package.enabled = False
                package.status = IntegrationPackageStatus.INCOMPATIBLE
                package.last_error = "; ".join(compatibility_errors)
                package.manifest_json = manifest.to_json()
            await session.flush()
            raise BadRequestError(package.last_error or "PACKAGE_INCOMPATIBLE")
        package = existing or InstalledPackage(package_id=manifest.package_id, name=manifest.name, version=manifest.version, official=manifest.official, enabled=True, status=IntegrationPackageStatus.ENABLED, manifest_json=manifest.to_json())
        if existing is None:
            session.add(package)
            log.append(_log("create_record", "ok", "Installed package record created"))
        else:
            log.append(_log("create_record", "ok", "Package already installed; refreshed manifest"))
        package.name = manifest.name
        package.version = manifest.version
        package.official = manifest.official
        package.enabled = True
        package.status = IntegrationPackageStatus.ENABLED
        package.manifest_json = manifest.to_json()
        package.last_error = None
        log.extend(_registration_log(manifest.to_json()))
        if install_demo_data:
            log.extend(await install_demo_data_for_package(session, package_id))
        package.install_log_json = (package.install_log_json or []) + log
        package.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return package, log

    async def enable_package(self, session: AsyncSession, package_id: str) -> InstalledPackage:
        package = await _installed_or_404(session, package_id)
        errors = validate_compatibility(self.registry.get(package_id))
        if errors:
            package.status = IntegrationPackageStatus.INCOMPATIBLE
            package.enabled = False
            package.last_error = "; ".join(errors)
            await session.flush()
            raise BadRequestError(package.last_error)
        package.enabled = True
        package.status = IntegrationPackageStatus.ENABLED
        package.last_error = None
        package.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return package

    async def disable_package(self, session: AsyncSession, package_id: str) -> InstalledPackage:
        package = await _installed_or_404(session, package_id)
        package.enabled = False
        package.status = IntegrationPackageStatus.DISABLED
        package.updated_at = datetime.now(timezone.utc)
        await session.flush()
        return package

    async def uninstall_package(self, session: AsyncSession, package_id: str) -> None:
        package = await _installed_or_404(session, package_id)
        await session.delete(package)
        await session.flush()

    async def validate_compatibility(self, package_id: str) -> list[str]:
        return validate_compatibility(self.registry.get(package_id))


async def install_demo_data_for_package(session: AsyncSession, package_id: str) -> list[dict[str, Any]]:
    if package_id == "omh-package-onec":
        from app.integration_flows.service import install_two_odata_to_endpoint_preset
        from app.integration_bus.service import install_presets

        await install_presets(session)
        await install_two_odata_to_endpoint_preset(session)
        return [_log("install_demo_data", "ok", "Installed 1C bus presets and visual OData flow preset")]
    if package_id == "omh-package-printer":
        return [_log("install_demo_data", "ok", "Printer package has no destructive demo data; printing scenarios remain available in Scenario Library")]
    return [_log("install_demo_data", "skipped", "No demo data installer registered")]


async def _installed_or_404(session: AsyncSession, package_id: str) -> InstalledPackage:
    package = await repository.get_installed(session, package_id)
    if package is None:
        raise NotFoundError("Installed package not found")
    return package


def _registration_log(manifest_json: dict[str, Any]) -> list[dict[str, Any]]:
    backend = manifest_json.get("backend") or {}
    frontend = manifest_json.get("frontend") or {}
    return [
        _log("register_backend", "ok", f"Routers: {len(backend.get('routers') or [])}, connectors: {len(backend.get('connectors') or [])}, steps: {len(backend.get('steps') or [])}"),
        _log("register_frontend", "ok", f"Pages: {len(frontend.get('pages') or [])}, navigation: {len(frontend.get('navigation') or [])}"),
        _log("install_presets", "ok", "Preset references registered; user data not overwritten"),
    ]


def _log(action: str, status: str, message: str) -> dict[str, Any]:
    return {"at": datetime.now(timezone.utc).isoformat(), "action": action, "status": status, "message": message}
