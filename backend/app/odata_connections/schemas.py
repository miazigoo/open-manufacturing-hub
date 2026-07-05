from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.enums import HealthStatus
from app.secrets.redaction import mask_config


class ODataConnectionRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    connector_id: UUID
    base_url: str
    auth_type: str = "none"
    username: str | None = None
    password_secret: str | None = None
    timeout_seconds: int = 20
    verify_ssl: bool = True
    default_top: int = 100
    max_pages: int = 10
    tags: list[str] = Field(default_factory=list)
    enabled: bool
    status: str
    last_health_status: HealthStatus | None = None
    last_health_message: str | None = None
    last_health_at: datetime | None = None
    config_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("config_json")
    def serialize_config_json(self, value: dict[str, Any]):
        return mask_config(value)


class ODataConnectionCreate(BaseModel):
    name: str
    description: str | None = None
    connector_id: UUID | None = None
    base_url: str
    auth_type: str = "basic"
    username: str | None = None
    password: str | None = None
    password_secret: str | None = None
    timeout_seconds: int = Field(default=20, ge=1)
    verify_ssl: bool = True
    default_top: int = Field(default=100, ge=1)
    max_pages: int = Field(default=10, ge=1)
    tags: list[str] = Field(default_factory=list)


class ODataConnectionPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    base_url: str | None = None
    auth_type: str | None = None
    username: str | None = None
    password: str | None = None
    password_secret: str | None = None
    timeout_seconds: int | None = Field(default=None, ge=1)
    verify_ssl: bool | None = None
    default_top: int | None = Field(default=None, ge=1)
    max_pages: int | None = Field(default=None, ge=1)
    tags: list[str] | None = None
    enabled: bool | None = None


class ODataConnectionOption(BaseModel):
    id: UUID
    connector_id: UUID
    label: str
    base_url: str
    enabled: bool
    tags: list[str] = Field(default_factory=list)


class ODataConnectionTestRequest(BaseModel):
    resource: str = "$metadata"
    top: int | None = Field(default=5, ge=1, le=100)
    filter: str | None = None


class ODataConnectionTestResponse(BaseModel):
    success: bool
    status: str
    message: str
    connector_id: UUID
    request: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] = Field(default_factory=dict)
    sample_items: list[dict[str, Any]] = Field(default_factory=list)
