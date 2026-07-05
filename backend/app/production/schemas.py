from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductionCheck(BaseModel):
    name: str
    status: Literal["ok", "warning", "error"]
    message: str | None = None
    details: dict[str, Any] | None = None


class ProductionStatus(BaseModel):
    app_env: str
    production_mode: bool
    version: str
    database_revision: str | None
    packages: list[dict[str, Any]]
    warnings: list[str]
    update_mode_enabled: bool = False
    current_environment: dict[str, Any] | None = None
    pending_change_sets: int = 0
    last_applied_change_set: dict[str, Any] | None = None


class SystemSnapshot(BaseModel):
    app_version: str
    backend_version: str
    frontend_version: str | None = None
    app_env: str
    production_mode: bool
    database_revision: str | None
    migration_head: str | None
    packages: list[dict[str, Any]]
    counts: dict[str, int]
    queue: dict[str, int]
    dlq_count: int
    auth_users_count: int | None = None
    current_environment: dict[str, Any] | None = None
    pending_change_sets: int = 0
    last_applied_change_set: dict[str, Any] | None = None
    last_backup_at: datetime | None = None
    health: dict[str, Any]
    warnings: list[str]
    update_mode: dict[str, Any]


class BackupRecordRead(BaseModel):
    id: UUID
    backup_type: str
    status: str
    file_path: str | None = None
    size_bytes: int | None = None
    created_at: datetime
    finished_at: datetime | None = None
    created_by: str | None = None
    error_message: str | None = None
    metadata_json: dict[str, Any] | None = None
    model_config = ConfigDict(from_attributes=True)


class ExportConfigRequest(BaseModel):
    secrets_policy: Literal["masked", "references_only"] = "masked"
    include_runtime: bool = False
    created_by: str | None = None


class ExportConfigResponse(BaseModel):
    export_id: UUID
    file_name: str
    size_bytes: int
    warnings: list[str]
    download_url: str


class ImportConfigRequest(BaseModel):
    export: dict[str, Any]
    mode: Literal["create_only", "upsert"] = "create_only"


class ImportPreview(BaseModel):
    valid: bool
    mode: str
    will_create: dict[str, int]
    will_update: dict[str, int]
    conflicts: list[dict[str, Any]]
    warnings: list[str]


class ImportApplyResponse(ImportPreview):
    applied: bool


class UpdateModeRequest(BaseModel):
    message: str | None = None
    enabled_by: str | None = None


class UpdateModeStatus(BaseModel):
    enabled: bool
    message: str | None = None
    enabled_at: datetime | None = None
    enabled_by: str | None = None


class UpdateCheckResponse(BaseModel):
    safe_to_update: bool
    checks: list[ProductionCheck]
    required_actions: list[str]


class DoctorResponse(BaseModel):
    generated_at: str
    app_env: str
    status: Literal["ok", "warning", "error"]
    summary: dict[str, int]
    checks: list[ProductionCheck]
    counts: dict[str, int]


class FirstRunChecklistItem(BaseModel):
    code: str
    title: str
    status: Literal["ok", "warning", "action_required", "manual"]
    details: dict[str, Any]


class FirstRunChecklistResponse(BaseModel):
    generated_at: str
    complete: bool
    items: list[FirstRunChecklistItem]
