from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.change_sets.models import ChangeSetOperation, ChangeSetStatus


class ConfigObjectRef(BaseModel):
    object_type: str
    object_id: UUID


class ChangeSetFromDraftsRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    object_refs: list[ConfigObjectRef]
    include_dependencies: bool = True


class ChangeSetItemRead(BaseModel):
    id: UUID
    change_set_id: UUID
    object_type: str
    object_id: str | None = None
    object_name: str | None = None
    operation: ChangeSetOperation
    config_json: dict[str, Any]
    version_id: UUID | None = None
    package_id: str | None = None
    dependencies_json: dict[str, Any] | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ChangeSetRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    source_environment: str | None = None
    target_environment: str | None = None
    status: ChangeSetStatus
    created_by: str | None = None
    created_at: datetime
    exported_at: datetime | None = None
    applied_at: datetime | None = None
    metadata_json: dict[str, Any] | None = None
    items: list[ChangeSetItemRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class ChangeSetExport(BaseModel):
    omh_change_set_version: int = 1
    name: str
    description: str | None = None
    created_at: str
    source_environment: str | None = None
    required_packages: list[dict[str, Any]] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    secrets_policy: str = "references_only"
    warnings: list[str] = Field(default_factory=list)


class ChangeSetImportMapping(BaseModel):
    connector_mapping: dict[str, str] = Field(default_factory=dict)
    secret_mapping: dict[str, str] = Field(default_factory=dict)
    environment_variables: dict[str, Any] = Field(default_factory=dict)
    allow_conflicts: bool = False
    run_smoke_tests: bool = False


class ChangeSetImportPreviewRequest(BaseModel):
    change_set: dict[str, Any]
    mapping: ChangeSetImportMapping = Field(default_factory=ChangeSetImportMapping)


class ChangeSetImportApplyRequest(ChangeSetImportPreviewRequest):
    pass


class ChangeSetImportPreview(BaseModel):
    valid: bool
    change_set_id: UUID | None = None
    will_create: list[dict[str, Any]] = Field(default_factory=list)
    will_update: list[dict[str, Any]] = Field(default_factory=list)
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    missing_packages: list[dict[str, Any]] = Field(default_factory=list)
    missing_secrets: list[dict[str, Any]] = Field(default_factory=list)
    missing_environment_variables: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ChangeSetImportApplyResponse(ChangeSetImportPreview):
    applied: bool = False
    applied_change_set_id: UUID | None = None
    applied_items: list[dict[str, Any]] = Field(default_factory=list)
    smoke: dict[str, Any] | None = None


class ChangeSetSmokeResult(BaseModel):
    passed: int
    failed: int
    results: list[dict[str, Any]]
