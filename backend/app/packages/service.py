from __future__ import annotations

import importlib
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import IntegrationPackageStatus
from app.core.errors import NotFoundError
from app.packages.compatibility import core_version, validate_compatibility
from app.packages.installer import PackageInstaller, install_demo_data_for_package
from app.packages.manifest import PackageManifest
from app.packages.registry import package_registry
from app.packages import repository

logger = logging.getLogger(__name__)


async def available_packages(session: AsyncSession) -> list[dict[str, Any]]:
    installed = {item.package_id: item for item in await repository.list_installed(session)}
    items = []
    for manifest in package_registry.list_packages():
        package = installed.get(manifest.package_id)
        errors = validate_compatibility(manifest)
        items.append({"manifest": manifest, "installed": package is not None, "enabled": bool(package and package.enabled), "status": package.status if package else None, "compatible": not errors, "compatibility_errors": errors})
    return items


async def installed_packages(session: AsyncSession):
    return await repository.list_installed(session)


async def package_details(session: AsyncSession, package_id: str) -> dict[str, Any]:
    manifest = package_registry.get(package_id)
    installed = await repository.get_installed(session, package_id)
    errors = validate_compatibility(manifest)
    return {"manifest": manifest, "installed": installed is not None, "enabled": bool(installed and installed.enabled), "status": installed.status if installed else None, "compatible": not errors, "compatibility_errors": errors}


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
        enabled = package.enabled if package is not None else False
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
    }


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
    await session.flush()


def _load_doc_ref(ref: str | None) -> str | None:
    if not ref:
        return None
    if ":" not in ref:
        return None
    module_name, attr = ref.split(":", 1)
    module = importlib.import_module(module_name)
    value = getattr(module, attr, None)
    return value if isinstance(value, str) else None
