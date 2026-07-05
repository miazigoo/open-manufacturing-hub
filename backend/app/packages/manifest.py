from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PackageFrontendPage(BaseModel):
    route: str
    title: str
    component: str | None = None


class PackageNavigationItem(BaseModel):
    group: str = "Integration Packages"
    title: str
    route: str


class PackageBackendManifest(BaseModel):
    modules: list[str] = Field(default_factory=list)
    routers: list[str] = Field(default_factory=list)
    connectors: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)


class PackageFrontendManifest(BaseModel):
    pages: list[PackageFrontendPage] = Field(default_factory=list)
    navigation: list[PackageNavigationItem] = Field(default_factory=list)


class PackageDocsManifest(BaseModel):
    readme: str | None = None
    quick_start: str | None = None


class PackageI18nManifest(BaseModel):
    namespaces: list[str] = Field(default_factory=list)
    locales: dict[str, str] = Field(default_factory=dict)


class PackageDependency(BaseModel):
    package_id: str
    version_min: str | None = None
    optional: bool = False
    reason: str | None = None


class PackageManifest(BaseModel):
    package_id: str
    name: str
    version: str
    description: str
    publisher: str = "OMH"
    official: bool = False
    core_version_min: str = "0.1.0"
    core_version_max: str | None = "0.2.x"
    category: str = "integration"
    capabilities: list[str] = Field(default_factory=list)
    status: str = "available"
    installable: bool = True
    expected_version: str | None = None
    expected_date: str | None = None
    planned_capabilities: list[str] = Field(default_factory=list)
    replacement_package_id: str | None = None
    reason_unavailable: str | None = None
    backend: PackageBackendManifest = Field(default_factory=PackageBackendManifest)
    frontend: PackageFrontendManifest = Field(default_factory=PackageFrontendManifest)
    presets: dict[str, Any] = Field(default_factory=dict)
    docs: PackageDocsManifest = Field(default_factory=PackageDocsManifest)
    i18n: PackageI18nManifest = Field(default_factory=PackageI18nManifest)
    extension_points: list[str] = Field(default_factory=list)
    dependencies: list[PackageDependency] = Field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
