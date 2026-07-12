from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DataContractKind = Literal["input", "output", "operation_request", "operation_response", "intermediate"]
DataContractOwnerType = Literal["operation_profile", "integration_pattern", "package"]
DataContractFieldType = Literal["string", "number", "boolean", "null", "object", "array", "date", "datetime", "guid", "raw"]


class DataContractField(BaseModel):
    path: str = Field(min_length=1, max_length=240)
    type: DataContractFieldType = "raw"
    required: bool = False
    label: str | None = None
    description: str | None = None
    example: Any = None
    default: Any = None


class DataContractSchema(BaseModel):
    type: Literal["object"] = "object"
    fields: list[DataContractField] = Field(default_factory=list)


class DataContractBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=180)
    kind: DataContractKind
    owner_type: DataContractOwnerType | None = None
    owner_id: UUID | None = None
    description: str | None = None
    schema_json: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "fields": []})
    example_json: dict[str, Any] | list[Any] | None = None


class DataContractCreate(DataContractBase):
    pass


class DataContractPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=180)
    kind: DataContractKind | None = None
    owner_type: DataContractOwnerType | None = None
    owner_id: UUID | None = None
    description: str | None = None
    schema_json: dict[str, Any] | None = None
    example_json: dict[str, Any] | list[Any] | None = None


class DataContractRead(DataContractBase):
    id: UUID
    fields: list[DataContractField] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
