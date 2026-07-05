from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.environments.models import EnvironmentType


class EnvironmentVariableCreate(BaseModel):
    key: str = Field(min_length=1, max_length=160)
    value_json: Any = None
    secret_ref: str | None = None
    description: str | None = None


class EnvironmentVariablePatch(BaseModel):
    value_json: Any = None
    secret_ref: str | None = None
    description: str | None = None


class EnvironmentVariableRead(BaseModel):
    id: UUID
    environment_id: UUID
    key: str
    value_json: Any = None
    secret_ref: str | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class EnvironmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code: str = Field(min_length=1, max_length=80)
    environment_type: EnvironmentType = EnvironmentType.CUSTOM
    description: str | None = None
    is_current: bool = False
    base_url: str | None = None
    variables: list[EnvironmentVariableCreate] = Field(default_factory=list)


class EnvironmentPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    code: str | None = Field(default=None, min_length=1, max_length=80)
    environment_type: EnvironmentType | None = None
    description: str | None = None
    is_current: bool | None = None
    base_url: str | None = None


class EnvironmentRead(BaseModel):
    id: UUID
    name: str
    code: str
    environment_type: EnvironmentType
    description: str | None = None
    is_current: bool
    base_url: str | None = None
    created_at: datetime
    updated_at: datetime
    variables: list[EnvironmentVariableRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)
