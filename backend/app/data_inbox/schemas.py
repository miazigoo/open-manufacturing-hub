from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

FIELD_TYPES = {"string", "number", "boolean", "guid", "date", "datetime", "array", "object", "raw"}
MISSING_POLICIES = {"reject", "accept_warning", "fill_defaults"}
STORAGE_MODES = {"none", "days", "forever"}
INPUT_MODES = {"json", "xml", "raw_text"}


class InboxField(BaseModel):
    path: str = Field(min_length=1, max_length=255)
    type: str = "string"
    required: bool = False
    default: Any = None

    @model_validator(mode="after")
    def check_type(self):
        if self.type not in FIELD_TYPES:
            raise ValueError(f"Unsupported field type: {self.type}")
        return self


class InboxTemplateCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    enabled: bool = True
    input_mode: str = "json"
    schema_json: dict[str, Any] = Field(default_factory=lambda: {"fields": []})
    missing_policy: str = "reject"
    storage_mode: str = "days"
    storage_days: int = Field(default=30, ge=1, le=3650)
    response_json: dict[str, Any] | None = None
    auth_token: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def check_enums(self):
        if self.input_mode not in INPUT_MODES:
            raise ValueError(f"Unsupported input_mode: {self.input_mode}")
        if self.missing_policy not in MISSING_POLICIES:
            raise ValueError(f"Unsupported missing_policy: {self.missing_policy}")
        if self.storage_mode not in STORAGE_MODES:
            raise ValueError(f"Unsupported storage_mode: {self.storage_mode}")
        return self


class InboxTemplatePatch(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=160, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    enabled: bool | None = None
    input_mode: str | None = None
    schema_json: dict[str, Any] | None = None
    missing_policy: str | None = None
    storage_mode: str | None = None
    storage_days: int | None = Field(default=None, ge=1, le=3650)
    response_json: dict[str, Any] | None = None
    auth_token: str | None = Field(default=None, max_length=255)


class InboxTemplateRead(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None
    enabled: bool
    input_mode: str
    schema_json: dict[str, Any]
    missing_policy: str
    storage_mode: str
    storage_days: int
    response_json: dict[str, Any] | None
    auth_token_set: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InboxRecordRead(BaseModel):
    id: UUID
    template_id: UUID
    status: str
    payload_json: dict[str, Any]
    fields_json: dict[str, Any]
    warnings_json: list[dict[str, Any]]
    source_ip: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InboxRecordPatch(BaseModel):
    payload_json: dict[str, Any] | None = None
    fields_json: dict[str, Any] | None = None


class InboxTemplateTestRequest(BaseModel):
    payload: Any = None
    text: str | None = None


class InboxTemplateTestResponse(BaseModel):
    status: str
    fields: dict[str, Any]
    warnings: list[dict[str, Any]]
    response: dict[str, Any]


class InboxResendRequest(BaseModel):
    url: str | None = Field(default=None, max_length=2000)
    flow_slug: str | None = Field(default=None, max_length=160)
    timeout_seconds: float = Field(default=30.0, gt=0, le=300)


class InboxResendResponse(BaseModel):
    success: bool
    status: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
