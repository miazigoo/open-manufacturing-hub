from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ResolverStrategy = Literal["odata", "rest", "static_map", "chain"]
CacheStatus = Literal["disabled", "miss", "hit", "stored", "expired", "bypass"]


class ResolverDefinitionBase(BaseModel):
    name: str
    resolver_code: str
    object_type: str
    enabled: bool = True
    strategy: ResolverStrategy
    connector_id: UUID | None = None
    input_schema_json: dict[str, Any] = Field(default_factory=dict)
    output_schema_json: dict[str, Any] | None = None
    config_json: dict[str, Any] = Field(default_factory=dict)
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600


class ResolverDefinitionCreate(ResolverDefinitionBase):
    pass


class ResolverDefinitionPatch(BaseModel):
    name: str | None = None
    resolver_code: str | None = None
    object_type: str | None = None
    enabled: bool | None = None
    strategy: ResolverStrategy | None = None
    connector_id: UUID | None = None
    input_schema_json: dict[str, Any] | None = None
    output_schema_json: dict[str, Any] | None = None
    config_json: dict[str, Any] | None = None
    cache_enabled: bool | None = None
    cache_ttl_seconds: int | None = None


class ResolverDefinitionRead(ResolverDefinitionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResolverResolveRequest(BaseModel):
    input_data: dict[str, Any] = Field(default_factory=dict, alias="input")
    context: dict[str, Any] | None = None
    use_cache: bool = True


class ResolverArtifact(BaseModel):
    name: str
    type: str
    payload: dict[str, Any]


class ResolverResult(BaseModel):
    success: bool
    resolver_code: str
    object_type: str | None = None
    object_json: dict[str, Any] | None = None
    cache_status: CacheStatus | str = "disabled"
    source: dict[str, Any] = Field(default_factory=dict)
    error_code: str | None = None
    error_message: str | None = None
    artifacts: list[ResolverArtifact] = Field(default_factory=list)


class ResolverCacheRead(BaseModel):
    id: UUID
    resolver_id: UUID
    resolver_code: str
    cache_key: str
    input_hash: str
    object_type: str
    resolved_object_json: dict[str, Any]
    source_connector_id: UUID | None
    source_system: str | None
    expires_at: datetime | None
    hit_count: int
    last_hit_at: datetime | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
