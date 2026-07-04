from __future__ import annotations
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field

class ODataResourceList(BaseModel):
    connector_id: UUID
    resources: list[str]
    metadata_preview: str | None = None
    fallback: bool = False

class ODataQueryRequest(BaseModel):
    resource: str
    top: int | None = Field(default=10, ge=1, le=500)
    filter: str | None = None
    select: str | None = None
    orderby: str | None = None

class ODataQueryResponse(BaseModel):
    request_url: str | None = None
    request: dict[str, Any]
    response: dict[str, Any]
    items: list[dict[str, Any]]
    count: int
    artifact_ids: dict[str, str] = Field(default_factory=dict)

class ODataLookupCreateRequest(BaseModel):
    name: str
    resource: str
    filter_template: str
    extract_json: dict[str, str] = Field(default_factory=dict)
    input_schema_json: dict[str, Any] | None = None
    required: bool = True
    cache_ttl_seconds: int | None = None
