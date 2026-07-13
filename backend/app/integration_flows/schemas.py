from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import EndpointProcessingMode, IntegrationFlowSourceType, IntegrationFlowTargetType


class EndpointBuilderConfig(BaseModel):
    input_mode: str = "json"
    response_mode: str = "accepted_event"
    processing_mode: EndpointProcessingMode = EndpointProcessingMode.ASYNC_QUEUE
    auth_mode: str = "none"
    auth_config_json: dict[str, Any] = Field(default_factory=dict)


class IntegrationFlowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9][a-z0-9_-]*[a-z0-9]$|^[a-z0-9]$")
    description: str | None = None
    enabled: bool = True
    source_type: IntegrationFlowSourceType = IntegrationFlowSourceType.ONEC
    target_type: IntegrationFlowTargetType = IntegrationFlowTargetType.EXTERNAL_API
    endpoint: EndpointBuilderConfig = Field(default_factory=EndpointBuilderConfig)
    matcher_group_json: dict[str, Any] = Field(default_factory=lambda: {"mode": "all", "rules": [{"type": "always"}]})
    action_json: dict[str, Any] = Field(default_factory=lambda: {"type": "create_event_only"})
    response_config_json: dict[str, Any] = Field(default_factory=dict)
    builder_json: dict[str, Any] | None = None
    test_payload_json: dict[str, Any] | None = None
    test_payload_text: str | None = None


class IntegrationFlowPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    matcher_group_json: dict[str, Any] | None = None
    action_json: dict[str, Any] | None = None
    response_config_json: dict[str, Any] | None = None
    builder_json: dict[str, Any] | None = None
    test_payload_json: dict[str, Any] | None = None
    test_payload_text: str | None = None


class IntegrationFlowRead(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    enabled: bool
    source_type: IntegrationFlowSourceType
    target_type: IntegrationFlowTargetType
    endpoint_id: UUID | None
    route_id: UUID | None
    workflow_id: UUID | None
    compiled_workflow_id: UUID | None
    mapping_id: UUID | None
    target_connector_id: UUID | None
    operation_template_id: UUID | None
    matcher_group_json: dict[str, Any]
    action_json: dict[str, Any]
    response_config_json: dict[str, Any]
    builder_json: dict[str, Any] | None
    last_validation_json: dict[str, Any] | None
    compiled_at: datetime | None
    test_payload_json: dict[str, Any] | None
    test_payload_text: str | None
    endpoint_url: str
    curl_example: str
    onec_http_example: str
    package_warnings: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class FlowTestRequest(BaseModel):
    input_mode: str = "json"
    payload_json: dict[str, Any] | None = None
    payload_text: str | None = None
    headers_json: dict[str, str] = Field(default_factory=dict)
    dry_run: bool = False


class FlowTestResponse(BaseModel):
    matcher: dict[str, Any]
    target_action: dict[str, Any]
    bus_response: dict[str, Any] | None = None
    curl_example: str
    onec_http_example: str


class FlowExportResponse(BaseModel):
    flow: IntegrationFlowRead
    config: dict[str, Any]
