from __future__ import annotations

from pydantic import BaseModel, Field


class BusinessObjectField(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    description: str | None = None


class BusinessObjectSchema(BaseModel):
    object_type: str
    display_name: str
    description: str | None = None
    fields: list[BusinessObjectField] = Field(default_factory=list)
    identity_fields: list[str] = Field(default_factory=list)
