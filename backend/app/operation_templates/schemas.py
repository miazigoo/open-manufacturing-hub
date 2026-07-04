from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OperationTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    operation_code: str | None = Field(default=None, min_length=1, max_length=180)
    system_type: str = Field(min_length=1, max_length=100)
    operation: str = Field(min_length=1, max_length=160)
    direction: str = "outbound"
    input_mode: str | None = None
    output_mode: str | None = None
    target_connector_type: str | None = None
    default_body_mode: str | None = None
    default_content_type: str | None = None
    description: str | None = None
    enabled: bool = True
    request_schema_json: dict[str, Any] | None = None
    request_template_json: dict[str, Any] = Field(default_factory=dict)
    response_schema_json: dict[str, Any] | None = None
    example_request_json: dict[str, Any] | None = None
    example_response_json: dict[str, Any] | None = None
    default_workflow_id: UUID | None = None


class OperationTemplatePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    operation_code: str | None = Field(default=None, min_length=1, max_length=180)
    system_type: str | None = Field(default=None, min_length=1, max_length=100)
    operation: str | None = Field(default=None, min_length=1, max_length=160)
    direction: str | None = None
    input_mode: str | None = None
    output_mode: str | None = None
    target_connector_type: str | None = None
    default_body_mode: str | None = None
    default_content_type: str | None = None
    description: str | None = None
    enabled: bool | None = None
    request_schema_json: dict[str, Any] | None = None
    request_template_json: dict[str, Any] | None = None
    response_schema_json: dict[str, Any] | None = None
    example_request_json: dict[str, Any] | None = None
    example_response_json: dict[str, Any] | None = None
    default_workflow_id: UUID | None = None


class OperationTemplateRead(BaseModel):
    id: UUID
    name: str
    operation_code: str | None
    system_type: str
    operation: str
    direction: str
    input_mode: str | None
    output_mode: str | None
    target_connector_type: str | None
    default_body_mode: str | None
    default_content_type: str | None
    description: str | None
    enabled: bool
    request_schema_json: dict[str, Any] | None
    request_template_json: dict[str, Any]
    response_schema_json: dict[str, Any] | None
    example_request_json: dict[str, Any] | None
    example_response_json: dict[str, Any] | None
    default_workflow_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
