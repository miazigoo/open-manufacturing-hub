from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.packages.manifest import PackageManifest


class InstalledPackageRead(BaseModel):
    id: UUID
    package_id: str
    name: str
    version: str
    status: str
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
    registered: bool = True
    available: bool = True
    installed: bool = False
    enabled: bool = False
    status: str | None = None
    compatible: bool = True
    compatibility_errors: list[str] = Field(default_factory=list)
    dependency_errors: list[str] = Field(default_factory=list)
    dependency_warnings: list[str] = Field(default_factory=list)
    upgrade_available: bool = False


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
    installed: bool = False


class PackageDocsRead(BaseModel):
    package_id: str
    readme: str
    quick_start: str | None = None


class PackageExportRead(BaseModel):
    core_version: str
    installed_packages: list[dict[str, Any]]
    runtime_capabilities: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: str


class PackageCapabilityRead(BaseModel):
    id: UUID | None
    package_id: str
    capability_type: str
    capability_code: str
    enabled: bool
    metadata_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime | None
    model_config = ConfigDict(from_attributes=True)


class PackageCompatibilityItem(BaseModel):
    package_id: str
    name: str
    installed: bool
    enabled: bool
    status: str
    compatible: bool
    upgrade_available: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PackageCompatibilityReport(BaseModel):
    generated_at: str
    core_version: str
    packages: list[PackageCompatibilityItem]


class PackageRouteInventoryItem(BaseModel):
    path: str
    methods: list[str]
    package_id: str | None = None
    capability_code: str | None = None
    guarded: bool = False
    source: str = "core"


class PackageUpgradeRead(BaseModel):
    package_id: str
    installed_version: str | None = None
    available_version: str
    upgrade_available: bool
    status: str
