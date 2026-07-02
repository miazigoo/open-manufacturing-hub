from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MappingVersionPayload(BaseModel):
    rules_json: list[dict[str, Any]] = Field(default_factory=list)
    source_schema_json: dict[str, Any] = Field(default_factory=dict)
    target_schema_json: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class MappingCreate(BaseModel):
    name: str
    description: str | None = None
    source_entity: str | None = None
    target_entity: str | None = None
    initial_version: MappingVersionPayload


class MappingPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    source_entity: str | None = None
    target_entity: str | None = None


class MappingVersionCreate(MappingVersionPayload):
    pass


class MappingCloneRequest(BaseModel):
    notes: str | None = None


class MappingValidateRequest(BaseModel):
    rules_json: list[dict[str, Any]] = Field(default_factory=list)
    sample_payload: dict[str, Any] | None = None


class MappingExecuteRequest(BaseModel):
    payload: dict[str, Any]


class MappingVersionRead(BaseModel):
    id: UUID
    mapping_id: UUID
    version: int
    rules_json: list[dict[str, Any]]
    source_schema_json: dict[str, Any]
    target_schema_json: dict[str, Any]
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MappingRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    source_entity: str | None
    target_entity: str | None
    created_at: datetime
    updated_at: datetime
    versions: list[MappingVersionRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class MappingValidationRead(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    preview: dict[str, Any] | None = None


class MappingDiffRead(BaseModel):
    mapping_id: UUID
    left_version: int
    right_version: int
    added: list[dict[str, Any]] = Field(default_factory=list)
    removed: list[dict[str, Any]] = Field(default_factory=list)
    changed: list[dict[str, Any]] = Field(default_factory=list)


class MappingExecuteRead(BaseModel):
    output: dict[str, Any]
