from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

MappingSourceType = Literal["variable", "constant", "template", "dynamic_object_entry"]


class MappingFieldRule(BaseModel):
    target_path: str = Field(min_length=1, max_length=240)
    source_type: MappingSourceType = "variable"
    source: str | None = None
    value: Any = None
    preserve_type: bool = True
    allow_duplicate: bool = False


class MappingDynamicEntryRule(BaseModel):
    object_path: str = Field(min_length=1, max_length=240)
    key_source: str = Field(min_length=1, max_length=240)
    value_source: str = Field(min_length=1, max_length=240)
    preserve_type: bool = True


class MappingJson(BaseModel):
    version: int = 1
    target_contract_code: str | None = None
    fields: list[MappingFieldRule] = Field(default_factory=list)
    dynamic_entries: list[MappingDynamicEntryRule] = Field(default_factory=list)


class MappingIssue(BaseModel):
    error_code: str
    message: str
    path: str | None = None
    severity: Literal["error", "warning"] = "error"


class MappingProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=180)
    source_context_json: dict[str, Any] | None = None
    target_contract_id: UUID | None = None
    operation_profile_id: UUID | None = None
    mapping_json: dict[str, Any] = Field(default_factory=lambda: {"version": 1, "fields": [], "dynamic_entries": []})
    description: str | None = None
    package_id: str | None = None


class MappingProfileCreate(MappingProfileBase):
    pass


class MappingProfilePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=180)
    source_context_json: dict[str, Any] | None = None
    target_contract_id: UUID | None = None
    operation_profile_id: UUID | None = None
    mapping_json: dict[str, Any] | None = None
    description: str | None = None
    package_id: str | None = None


class MappingProfileRead(MappingProfileBase):
    id: UUID
    target_contract_name: str | None = None
    target_contract_code: str | None = None
    operation_profile_name: str | None = None
    operation_profile_code: str | None = None
    status: str = "draft"
    used_by: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MappingPreviewRequest(BaseModel):
    mapping_profile_id: UUID | None = None
    mapping_json: dict[str, Any] | None = None
    source_context_json: dict[str, Any] | None = None
    target_contract_id: UUID | None = None


class MappingValidateRequest(BaseModel):
    mapping_profile_id: UUID | None = None
    mapping_json: dict[str, Any] | None = None
    source_context_json: dict[str, Any] | None = None
    target_contract_id: UUID | None = None


class MappingPreviewSummary(BaseModel):
    root_type: str
    top_level_keys: list[str] = Field(default_factory=list)
    truncated_arrays: dict[str, int] = Field(default_factory=dict)


class MappingRenderResponse(BaseModel):
    success: bool
    payload: Any = None
    preview: Any = None
    errors: list[MappingIssue] = Field(default_factory=list)
    warnings: list[MappingIssue] = Field(default_factory=list)
    summary: MappingPreviewSummary | None = None


class MappingValidationResponse(BaseModel):
    valid: bool
    errors: list[MappingIssue] = Field(default_factory=list)
    warnings: list[MappingIssue] = Field(default_factory=list)


class MappingPresetsResponse(BaseModel):
    contracts: list[dict[str, Any]] = Field(default_factory=list)
    mappings: list[dict[str, Any]] = Field(default_factory=list)


class InstallMappingPresetsResponse(BaseModel):
    contracts: list[Any] = Field(default_factory=list)
    mappings: list[MappingProfileRead] = Field(default_factory=list)
    linked_operations: list[str] = Field(default_factory=list)
