from __future__ import annotations

import importlib
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import IntegrationPackageStatus
from app.core.errors import NotFoundError
from app.packages.compatibility import core_version, validate_compatibility
from app.packages.installer import PackageInstaller, install_demo_data_for_package, validate_dependencies
from app.packages.manifest import PackageManifest
from app.packages.registry import package_registry
from app.packages.runtime import capability_dict, list_runtime_capabilities, manifest_capabilities, sync_all_installed_capabilities
from app.packages import repository

logger = logging.getLogger(__name__)


async def available_packages(session: AsyncSession) -> list[dict[str, Any]]:
    installed = {item.package_id: item for item in await repository.list_installed(session)}
    items = []
    for manifest in package_registry.list_packages():
        package = installed.get(manifest.package_id)
        errors = validate_compatibility(manifest)
        dependency_errors = await validate_dependencies(session, manifest)
        dependency_warnings = await _dependency_warnings(session, manifest)
        items.append({"manifest": manifest, "installed": package is not None, "enabled": bool(package and package.enabled), "status": package.status if package else None, "compatible": not errors and not dependency_errors, "compatibility_errors": errors, "dependency_errors": dependency_errors, "dependency_warnings": dependency_warnings, "upgrade_available": _upgrade_available(package.version, manifest.version) if package else False})
    return items


async def installed_packages(session: AsyncSession):
    return await repository.list_installed(session)


async def package_details(session: AsyncSession, package_id: str) -> dict[str, Any]:
    manifest = package_registry.get(package_id)
    installed = await repository.get_installed(session, package_id)
    errors = validate_compatibility(manifest)
    dependency_errors = await validate_dependencies(session, manifest)
    return {"manifest": manifest, "installed": installed is not None, "enabled": bool(installed and installed.enabled), "status": installed.status if installed else None, "compatible": not errors and not dependency_errors, "compatibility_errors": errors, "dependency_errors": dependency_errors, "dependency_warnings": await _dependency_warnings(session, manifest), "upgrade_available": _upgrade_available(installed.version, manifest.version) if installed else False}


async def install_package(session: AsyncSession, package_id: str, *, install_demo_data: bool = False):
    return await PackageInstaller().install_package(session, package_id, install_demo_data=install_demo_data)


async def enable_package(session: AsyncSession, package_id: str):
    return await PackageInstaller().enable_package(session, package_id)


async def disable_package(session: AsyncSession, package_id: str):
    return await PackageInstaller().disable_package(session, package_id)


async def uninstall_package(session: AsyncSession, package_id: str) -> None:
    await PackageInstaller().uninstall_package(session, package_id)


async def install_demo_data(session: AsyncSession, package_id: str) -> list[dict[str, Any]]:
    package = await repository.get_installed(session, package_id)
    if package is None:
        raise NotFoundError("Installed package not found")
    log = await install_demo_data_for_package(session, package_id)
    package.install_log_json = (package.install_log_json or []) + log
    package.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return log


async def package_navigation(session: AsyncSession) -> list[dict[str, Any]]:
    installed = {item.package_id: item for item in await repository.list_installed(session)}
    items: list[dict[str, Any]] = []
    for manifest in package_registry.list_packages():
        package = installed.get(manifest.package_id)
        enabled = bool(package and package.enabled and package.status == IntegrationPackageStatus.ENABLED)
        for item in manifest.frontend.navigation:
            items.append({"package_id": manifest.package_id, "group": item.group, "title": item.title, "route": item.route, "enabled": enabled})
    return sorted(items, key=lambda item: (item["group"], item["title"]))


async def package_docs(session: AsyncSession, package_id: str) -> dict[str, Any]:
    manifest = package_registry.get(package_id)
    readme = _load_doc_ref(manifest.docs.readme) or f"# {manifest.name}\n\n{manifest.description}"
    quick_start = _load_doc_ref(manifest.docs.quick_start)
    return {"package_id": package_id, "readme": readme, "quick_start": quick_start}


async def export_config(session: AsyncSession) -> dict[str, Any]:
    packages = await repository.list_installed(session)
    capabilities = await list_runtime_capabilities(session)
    return {
        "core_version": core_version(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "installed_packages": [
            {
                "package_id": package.package_id,
                "name": package.name,
                "version": package.version,
                "status": package.status.value,
                "enabled": package.enabled,
                "official": package.official,
                "manifest": package.manifest_json,
            }
            for package in packages
        ],
        "runtime_capabilities": [capability_dict(row) for row in capabilities],
    }


async def package_capabilities(session: AsyncSession, package_id: str | None = None) -> list[dict[str, Any]]:
    package = None
    if package_id:
        package = await repository.get_installed(session, package_id)
        if package is None:
            manifest = package_registry.get(package_id)
            return [
                {
                    "id": None,
                    "package_id": manifest.package_id,
                    "capability_type": capability.type,
                    "capability_code": capability.code,
                    "enabled": False,
                    "metadata_json": capability.metadata,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }
                for capability in manifest_capabilities(manifest)
            ]
    rows = await list_runtime_capabilities(session, package_id)
    if package_id and package and not rows:
        await sync_all_installed_capabilities(session)
        rows = await list_runtime_capabilities(session, package_id)
    return [capability_dict(row) for row in rows]


async def compatibility_report(session: AsyncSession) -> dict[str, Any]:
    installed = {item.package_id: item for item in await repository.list_installed(session)}
    packages: list[dict[str, Any]] = []
    for manifest in package_registry.list_packages():
        package = installed.get(manifest.package_id)
        compatibility_errors = validate_compatibility(manifest)
        dependency_errors = await validate_dependencies(session, manifest)
        warnings = await _dependency_warnings(session, manifest)
        errors = compatibility_errors + dependency_errors
        packages.append(
            {
                "package_id": manifest.package_id,
                "name": manifest.name,
                "installed": package is not None,
                "enabled": bool(package and package.enabled),
                "status": package.status.value if package else "available",
                "compatible": not errors,
                "upgrade_available": _upgrade_available(package.version, manifest.version) if package else False,
                "errors": errors,
                "warnings": warnings,
            }
        )
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "core_version": core_version(), "packages": packages}


async def check_upgrade(session: AsyncSession, package_id: str) -> dict[str, Any]:
    manifest = package_registry.get(package_id)
    package = await repository.get_installed(session, package_id)
    return {"package_id": package_id, "installed_version": package.version if package else None, "available_version": manifest.version, "upgrade_available": _upgrade_available(package.version, manifest.version) if package else False, "status": "installed" if package else "not_installed"}


async def mark_upgraded(session: AsyncSession, package_id: str):
    manifest = package_registry.get(package_id)
    package = await repository.get_installed(session, package_id)
    if package is None:
        raise NotFoundError("Installed package not found")
    package.version = manifest.version
    package.manifest_json = manifest.to_json()
    package.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await sync_all_installed_capabilities(session)
    return await check_upgrade(session, package_id)


def route_inventory(routes: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for route in routes:
        path = getattr(route, "path", None)
        if not path or not path.startswith("/api/"):
            continue
        package_id, capability_code = _route_package(path)
        result.append(
            {
                "path": path,
                "methods": sorted(method for method in getattr(route, "methods", set()) if method not in {"HEAD", "OPTIONS"}),
                "package_id": package_id,
                "capability_code": capability_code,
                "guarded": package_id is not None,
                "source": "package" if package_id else "core",
            }
        )
    result.extend(_fallback_route_inventory(result))
    return sorted(result, key=lambda item: item["path"])


async def startup_package_check(session: AsyncSession) -> None:
    try:
        packages = await repository.list_installed(session)
    except Exception as exc:  # pragma: no cover - defensive startup guard
        logger.warning("Package startup check skipped: %s", exc)
        return
    if not packages:
        logger.info("No integration packages installed yet")
        return
    for package in packages:
        try:
            manifest = PackageManifest.model_validate(package.manifest_json)
            errors = validate_compatibility(manifest)
            if errors:
                package.status = IntegrationPackageStatus.INCOMPATIBLE
                package.enabled = False
                package.last_error = "; ".join(errors)
                logger.warning("Integration package %s incompatible: %s", package.package_id, package.last_error)
            elif package.status == IntegrationPackageStatus.FAILED:
                logger.warning("Integration package %s is failed: %s", package.package_id, package.last_error)
            else:
                logger.info("Integration package loaded: %s %s enabled=%s", package.package_id, package.version, package.enabled)
        except Exception as exc:  # pragma: no cover - defensive startup guard
            package.status = IntegrationPackageStatus.FAILED
            package.enabled = False
            package.last_error = str(exc)
            logger.warning("Integration package %s failed startup validation: %s", package.package_id, exc)
    await sync_all_installed_capabilities(session)
    await session.flush()


def _load_doc_ref(ref: str | None) -> str | None:
    if not ref:
        return None
    if ":" not in ref:
        path = Path(ref)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[3] / ref
        if path.exists() and path.is_file():
            return path.read_text(encoding="utf-8")
        return None
    module_name, attr = ref.split(":", 1)
    module = importlib.import_module(module_name)
    value = getattr(module, attr, None)
    return value if isinstance(value, str) else None


async def _dependency_warnings(session: AsyncSession, manifest: PackageManifest) -> list[str]:
    warnings: list[str] = []
    for dependency in manifest.dependencies:
        package = await repository.get_installed(session, dependency.package_id)
        if dependency.optional and package is None:
            warnings.append(f"OPTIONAL_PACKAGE_NOT_INSTALLED: {manifest.package_id} can use {dependency.package_id}")
    return warnings


def _upgrade_available(installed_version: str, available_version: str) -> bool:
    return _version_tuple(installed_version) < _version_tuple(available_version)


def _version_tuple(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for part in value.replace("x", "0").split("-")[0].split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def _route_package(path: str) -> tuple[str | None, str | None]:
    if path.startswith(("/api/onec-workbench", "/api/odata-explorer", "/api/onec/xml", "/api/onec-scenarios", "/api/onec-templates")):
        return "omh-package-onec", path.split("/")[2]
    if path.startswith("/api/printing"):
        return "omh-package-printer", "printing"
    return None, None


def _fallback_route_inventory(existing: list[dict[str, Any]]) -> list[dict[str, Any]]:
    existing_paths = {item["path"] for item in existing}
    package_patterns = [
        ("/api/onec/xml/*", "omh-package-onec", "onec_workbench"),
        ("/api/onec-workbench/*", "omh-package-onec", "onec_workbench"),
        ("/api/odata-explorer/*", "omh-package-onec", "odata_explorer"),
        ("/api/onec-scenarios/*", "omh-package-onec", "onec_scenarios"),
        ("/api/onec-templates/*", "omh-package-onec", "onec_templates"),
        ("/api/printing/*", "omh-package-printer", "printing"),
        ("/api/packages/onec/*", "omh-package-onec", "packages_onec"),
        ("/api/packages/printer/*", "omh-package-printer", "packages_printer"),
    ]
    core_patterns = [
        "/api/bus/in/{slug}",
        "/api/events/*",
        "/api/queue/*",
        "/api/packages/*",
    ]
    fallback = [
        {"path": path, "methods": ["GET", "POST", "PATCH", "DELETE"], "package_id": package_id, "capability_code": capability_code, "guarded": True, "source": "package"}
        for path, package_id, capability_code in package_patterns
        if path not in existing_paths
    ]
    fallback.extend({"path": path, "methods": ["GET", "POST", "PATCH", "DELETE"], "package_id": None, "capability_code": None, "guarded": False, "source": "core"} for path in core_patterns if path not in existing_paths)
    return fallback
