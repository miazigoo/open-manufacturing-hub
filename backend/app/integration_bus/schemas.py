from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

INPUT_MODES = {"json", "xml", "raw_text", "multipart_file", "form"}
RESPONSE_MODES = {"sync_response", "accepted_event", "accepted_message", "proxy_response"}
AUTH_MODES = {"none", "static_token"}


class IntegrationEndpointCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")
    enabled: bool = True
    description: str | None = None
    input_mode: str = "json"
    response_mode: str = "accepted_event"
    default_source_system: str | None = None
    default_target_system: str | None = None
    default_event_type: str = "BusRequestReceived"
    default_entity_type: str | None = None
    workflow_id: UUID | None = None
    route_id: UUID | None = None
    operation_template_id: UUID | None = None
    auth_mode: str = "none"
    auth_config_json: dict[str, Any] = Field(default_factory=dict)


class IntegrationEndpointPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=160, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")
    enabled: bool | None = None
    description: str | None = None
    input_mode: str | None = None
    response_mode: str | None = None
    default_source_system: str | None = None
    default_target_system: str | None = None
    default_event_type: str | None = None
    default_entity_type: str | None = None
    workflow_id: UUID | None = None
    route_id: UUID | None = None
    operation_template_id: UUID | None = None
    auth_mode: str | None = None
    auth_config_json: dict[str, Any] | None = None


class IntegrationEndpointRead(BaseModel):
    id: UUID
    name: str
    slug: str
    enabled: bool
    description: str | None
    input_mode: str
    response_mode: str
    default_source_system: str | None
    default_target_system: str | None
    default_event_type: str
    default_entity_type: str | None
    workflow_id: UUID | None
    route_id: UUID | None
    operation_template_id: UUID | None
    auth_mode: str
    auth_config_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IntegrationRouteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    source_system: str | None = None
    target_system: str | None = None
    event_type: str | None = None
    message_type: str | None = None
    document_type: str | None = None
    operation: str | None = None
    condition_json: dict[str, Any] = Field(default_factory=dict)
    workflow_id: UUID | None = None
    mapping_id: UUID | None = None
    target_connector_id: UUID | None = None
    operation_template_id: UUID | None = None
    priority: int = 100


class IntegrationRoutePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    source_system: str | None = None
    target_system: str | None = None
    event_type: str | None = None
    message_type: str | None = None
    document_type: str | None = None
    operation: str | None = None
    condition_json: dict[str, Any] | None = None
    workflow_id: UUID | None = None
    mapping_id: UUID | None = None
    target_connector_id: UUID | None = None
    operation_template_id: UUID | None = None
    priority: int | None = None


class IntegrationRouteRead(BaseModel):
    id: UUID
    name: str
    enabled: bool
    source_system: str | None
    target_system: str | None
    event_type: str | None
    message_type: str | None
    document_type: str | None
    operation: str | None
    condition_json: dict[str, Any]
    workflow_id: UUID | None
    mapping_id: UUID | None
    target_connector_id: UUID | None
    operation_template_id: UUID | None
    priority: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ODataLookupTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    connector_id: UUID
    resource: str = Field(min_length=1, max_length=255)
    filter_template: str = Field(min_length=1)
    input_schema_json: dict[str, Any] | None = None
    extract_json: dict[str, str] = Field(default_factory=dict)
    required: bool = True
    cache_ttl_seconds: int | None = Field(default=None, gt=0)


class ODataLookupTemplatePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    connector_id: UUID | None = None
    resource: str | None = Field(default=None, min_length=1, max_length=255)
    filter_template: str | None = Field(default=None, min_length=1)
    input_schema_json: dict[str, Any] | None = None
    extract_json: dict[str, str] | None = None
    required: bool | None = None
    cache_ttl_seconds: int | None = Field(default=None, gt=0)


class ODataLookupTemplateRead(BaseModel):
    id: UUID
    name: str
    connector_id: UUID
    resource: str
    filter_template: str
    input_schema_json: dict[str, Any] | None
    extract_json: dict[str, Any]
    required: bool
    cache_ttl_seconds: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ODataLookupTemplateTestRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class BusDispatchResponse(BaseModel):
    accepted: bool = True
    event_id: UUID
    message_id: UUID | None = None
    status: str
    timeline_url: str
    route_id: UUID | None = None
    response: dict[str, Any] | None = None


class PresetInstallResponse(BaseModel):
    endpoints: list[IntegrationEndpointRead]
    routes: list[IntegrationRouteRead]
    lookups: list[ODataLookupTemplateRead]
