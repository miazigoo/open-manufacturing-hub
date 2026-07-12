from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.enums import HealthStatus
from app.secrets.redaction import mask_config

ConnectionProfileKind = Literal["onec_odata", "onec_http_service", "rest_api", "printer", "smb_share", "local_directory", "training_mock"]


class SecretReferenceRead(BaseModel):
    name: str
    path: str


class ConnectionProfileHealth(BaseModel):
    status: HealthStatus | None = None
    message: str | None = None
    checked_at: datetime | None = None


class ConnectionProfileRead(BaseModel):
    id: str
    connector_id: UUID
    name: str
    kind: ConnectionProfileKind
    description: str | None = None
    enabled: bool
    status: str
    training: bool = False
    package_id: str | None = None
    config_json: dict[str, Any] = Field(default_factory=dict)
    secret_refs: list[SecretReferenceRead] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    health: ConnectionProfileHealth = Field(default_factory=ConnectionProfileHealth)
    used_by: list[str] = Field(default_factory=list)
    read_only: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("config_json")
    def serialize_config_json(self, value: dict[str, Any]):
        return mask_config(value)


class ConnectionProfileCreate(BaseModel):
    name: str
    kind: ConnectionProfileKind
    description: str | None = None
    enabled: bool = True
    config_json: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    package_id: str | None = None


class ConnectionProfilePatch(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    config_json: dict[str, Any] | None = None
    tags: list[str] | None = None


class ConnectionProfileOption(BaseModel):
    id: str
    profile_id: str
    connector_id: UUID
    label: str
    name: str
    kind: ConnectionProfileKind
    enabled: bool
    training: bool = False
    base_url: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ConnectionCenterOptions(BaseModel):
    profiles: list[ConnectionProfileOption]
    by_kind: dict[str, list[ConnectionProfileOption]]


class ConnectionProfileTestRequest(BaseModel):
    dry_run: bool = True
    confirm_write: bool = False
    confirm_print: bool = False
    resource: str = "$metadata"
    top: int | None = Field(default=5, ge=1, le=100)
    filter: str | None = None
    health_path: str | None = None
    custom_path: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ConnectionProfileTestResponse(BaseModel):
    success: bool
    status: str
    message: str
    profile_id: str
    connector_id: UUID
    kind: ConnectionProfileKind
    dry_run: bool = True
    request: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] = Field(default_factory=dict)
    sample_items: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
