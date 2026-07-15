from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import Depends
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.enums import IntegrationPackageStatus
from app.core.errors import NotFoundError
from app.packages.capabilities import PackageCapability, capabilities_for_manifest
from app.packages.manifest import PackageManifest
from app.packages.models import InstalledPackage, PackageRuntimeCapability
from app.packages.registry import package_registry
from app.packages import repository


class PackageAccessError(Exception):
    def __init__(self, status_code: int, error: str, package_id: str, message: str) -> None:
        self.status_code = status_code
        self.error = error
        self.package_id = package_id
        self.message = message
        super().__init__(message)


def require_package_enabled(package_id: str) -> Callable[..., Any]:
    async def dependency(session: AsyncSession = Depends(get_session)) -> None:
        package = await repository.get_installed(session, package_id)
        if package is None:
            manifest_name = _manifest_name(package_id)
            raise PackageAccessError(404, "PACKAGE_NOT_INSTALLED", package_id, f"{manifest_name} is not installed")
        if not package.enabled or package.status != IntegrationPackageStatus.ENABLED:
            manifest_name = package.name or _manifest_name(package_id)
            raise PackageAccessError(403, "PACKAGE_DISABLED", package_id, f"{manifest_name} is disabled")

    return dependency


async def is_package_enabled(session: AsyncSession, package_id: str) -> bool:
    package = await repository.get_installed(session, package_id)
    return bool(package and package.enabled and package.status == IntegrationPackageStatus.ENABLED)


async def list_runtime_capabilities(session: AsyncSession, package_id: str | None = None) -> list[PackageRuntimeCapability]:
    stmt = select(PackageRuntimeCapability)
    if package_id:
        stmt = stmt.where(PackageRuntimeCapability.package_id == package_id)
    stmt = stmt.order_by(PackageRuntimeCapability.package_id, PackageRuntimeCapability.capability_type, PackageRuntimeCapability.capability_code)
    return list((await session.execute(stmt)).scalars().all())


async def enabled_capability_codes(session: AsyncSession, capability_type: str) -> set[str]:
    stmt = select(PackageRuntimeCapability.capability_code).where(PackageRuntimeCapability.capability_type == capability_type, PackageRuntimeCapability.enabled.is_(True))
    return set((await session.execute(stmt)).scalars().all())


async def sync_package_capabilities(session: AsyncSession, package: InstalledPackage, manifest: PackageManifest | None = None) -> list[PackageRuntimeCapability]:
    manifest = manifest or _manifest_from_package(package)
    now = datetime.now(timezone.utc)
    desired = capabilities_for_manifest(manifest)
    existing = {
        (item.capability_type, item.capability_code): item
        for item in (await session.execute(select(PackageRuntimeCapability).where(PackageRuntimeCapability.package_id == package.package_id))).scalars().all()
    }
    desired_keys = {(item.type, item.code) for item in desired}
    rows: list[PackageRuntimeCapability] = []
    for capability in desired:
        key = (capability.type, capability.code)
        row = existing.get(key)
        if row is None:
            row = PackageRuntimeCapability(package_id=package.package_id, capability_type=capability.type, capability_code=capability.code)
            session.add(row)
        row.enabled = bool(package.enabled and package.status == IntegrationPackageStatus.ENABLED)
        row.metadata_json = capability.metadata
        row.updated_at = now
        rows.append(row)
    for key, row in existing.items():
        if key not in desired_keys:
            row.enabled = False
            row.metadata_json = {**(row.metadata_json or {}), "removed_from_manifest": True}
            row.updated_at = now
    await session.flush()
    return rows


async def delete_package_capabilities(session: AsyncSession, package_id: str) -> None:
    await session.execute(delete(PackageRuntimeCapability).where(PackageRuntimeCapability.package_id == package_id))
    await session.flush()


async def sync_all_installed_capabilities(session: AsyncSession) -> None:
    for package in await repository.list_installed(session):
        try:
            manifest = package_registry.get(package.package_id)
        except NotFoundError:
            manifest = _manifest_from_package(package)
        await sync_package_capabilities(session, package, manifest)


def capability_dict(row: PackageRuntimeCapability) -> dict[str, Any]:
    return {
        "id": row.id,
        "package_id": row.package_id,
        "capability_type": row.capability_type,
        "capability_code": row.capability_code,
        "enabled": row.enabled,
        "metadata_json": row.metadata_json or {},
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def manifest_capabilities(manifest: PackageManifest) -> list[PackageCapability]:
    return capabilities_for_manifest(manifest)


def _manifest_from_package(package: InstalledPackage) -> PackageManifest:
    return PackageManifest.model_validate(package.manifest_json)


def _manifest_name(package_id: str) -> str:
    try:
        return package_registry.get(package_id).name
    except NotFoundError:
        return package_id
