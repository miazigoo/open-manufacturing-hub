from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OperationTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    system_type: str = Field(min_length=1, max_length=100)
    operation: str = Field(min_length=1, max_length=160)
    description: str | None = None
    enabled: bool = True
    request_template_json: dict[str, Any] = Field(default_factory=dict)
    response_schema_json: dict[str, Any] | None = None
    default_workflow_id: UUID | None = None


class OperationTemplatePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    system_type: str | None = Field(default=None, min_length=1, max_length=100)
    operation: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    enabled: bool | None = None
    request_template_json: dict[str, Any] | None = None
    response_schema_json: dict[str, Any] | None = None
    default_workflow_id: UUID | None = None


class OperationTemplateRead(BaseModel):
    id: UUID
    name: str
    system_type: str
    operation: str
    description: str | None
    enabled: bool
    request_template_json: dict[str, Any]
    response_schema_json: dict[str, Any] | None
    default_workflow_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
