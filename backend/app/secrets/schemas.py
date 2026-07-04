from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import SecretType


class SecretCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9_.:-]+$")
    description: str | None = None
    secret_type: SecretType = SecretType.GENERIC
    value: str = Field(min_length=1)


class SecretPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255, pattern=r"^[A-Za-z0-9_.:-]+$")
    description: str | None = None
    secret_type: SecretType | None = None
    enabled: bool | None = None


class SecretRotateRequest(BaseModel):
    value: str = Field(min_length=1)


class SecretRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    secret_type: SecretType
    value_preview: str | None
    enabled: bool
    reference: dict[str, str]
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None
    rotated_at: datetime | None
    created_by: str | None
    updated_by: str | None

    model_config = ConfigDict(from_attributes=True)


class SecretReferenceTestRequest(BaseModel):
    reference: dict[str, str] | str


class SecretReferenceTestResponse(BaseModel):
    valid: bool
    name: str | None = None
    status: Literal["ok", "missing", "disabled", "invalid"]
    value_preview: str | None = None
    message: str | None = None


class SecretConfigValidationRequest(BaseModel):
    config: dict[str, Any]


class SecretReferenceStatus(BaseModel):
    name: str
    status: Literal["ok", "missing", "disabled", "invalid"]
    path: str
    value_preview: str | None = None


class SecretConfigValidationResponse(BaseModel):
    valid: bool
    references: list[SecretReferenceStatus]
    raw_secret_warnings: list[str]
