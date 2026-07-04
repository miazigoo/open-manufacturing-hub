from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import IntegrationPackageStatus
from app.packages.manifest import PackageManifest


class InstalledPackageRead(BaseModel):
    id: UUID
    package_id: str
    name: str
    version: str
    status: IntegrationPackageStatus
    official: bool
    enabled: bool
    installed_at: datetime
    updated_at: datetime | None
    manifest_json: dict[str, Any]
    install_log_json: list[dict[str, Any]] | None
    last_error: str | None
    model_config = ConfigDict(from_attributes=True)


class PackageAvailableRead(BaseModel):
    manifest: PackageManifest
    installed: bool = False
    enabled: bool = False
    status: IntegrationPackageStatus | None = None
    compatible: bool = True
    compatibility_errors: list[str] = Field(default_factory=list)


class PackageInstallRequest(BaseModel):
    install_demo_data: bool = False


class PackageActionResponse(BaseModel):
    package: InstalledPackageRead
    log: list[dict[str, Any]] = Field(default_factory=list)


class PackageNavigationRead(BaseModel):
    package_id: str
    group: str
    title: str
    route: str
    enabled: bool = True


class PackageDocsRead(BaseModel):
    package_id: str
    readme: str
    quick_start: str | None = None


class PackageExportRead(BaseModel):
    core_version: str
    installed_packages: list[dict[str, Any]]
    generated_at: str
