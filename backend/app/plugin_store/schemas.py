from __future__ import annotations

from pydantic import BaseModel


class PluginStoreItem(BaseModel):
    package_id: str
    name: str
    version: str
    official: bool = False
    installed: bool = False
    enabled: bool = False
    category: str
    description: str


class PluginStoreCategory(BaseModel):
    category: str
    count: int
