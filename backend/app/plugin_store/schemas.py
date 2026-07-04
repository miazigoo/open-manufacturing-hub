from __future__ import annotations

from pydantic import BaseModel, Field


class PluginStoreItem(BaseModel):
    package_id: str
    name: str
    version: str
    official: bool = False
    registered: bool = True
    available: bool = True
    installed: bool = False
    enabled: bool = False
    category: str
    description: str
    status: str = "available"
    installable: bool = True
    expected_version: str | None = None
    expected_date: str | None = None
    planned_capabilities: list[str] = Field(default_factory=list)
    replacement_package_id: str | None = None
    reason_unavailable: str | None = None


class PluginStoreCategory(BaseModel):
    category: str
    count: int
