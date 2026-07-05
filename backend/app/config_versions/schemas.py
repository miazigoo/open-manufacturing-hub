from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.config_versions.models import ConfigVersionStatus, ConfigVersionTestStatus


class ConfigDraftRequest(BaseModel):
    config_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    comment: str | None = None


class ConfigDraftPatch(BaseModel):
    config_json: dict[str, Any] | None = None
    metadata_json: dict[str, Any] | None = None
    comment: str | None = None


class ConfigPublishRequest(BaseModel):
    version_id: UUID
    comment: str | None = None
    confirm_untested: bool = False


class ConfigRollbackRequest(BaseModel):
    target_version_id: UUID
    comment: str | None = None
    confirm_untested: bool = False


class ConfigVersionTestRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    input: dict[str, Any] | None = None
    use_cache: bool = False


class ConfigVersionRead(BaseModel):
    id: UUID
    object_type: str
    object_id: UUID
    object_name: str | None
    version_number: int
    status: ConfigVersionStatus
    config_json: dict[str, Any]
    metadata_json: dict[str, Any] | None
    created_by: str | None
    created_at: datetime
    updated_at: datetime
    published_by: str | None
    published_at: datetime | None
    archived_at: datetime | None
    rollback_of_version_id: UUID | None
    test_status: ConfigVersionTestStatus
    last_test_event_id: UUID | None
    last_test_run_at: datetime | None
    last_test_error: str | None
    comment: str | None

    model_config = ConfigDict(from_attributes=True)


class ConfigVersionsResponse(BaseModel):
    object_type: str
    object_id: UUID
    active_version: ConfigVersionRead | None
    draft_version: ConfigVersionRead | None
    versions: list[ConfigVersionRead]


class ConfigDiffResponse(BaseModel):
    from_version_id: UUID
    to_version_id: UUID
    added: list[dict[str, Any]] = Field(default_factory=list)
    removed: list[dict[str, Any]] = Field(default_factory=list)
    changed: list[dict[str, Any]] = Field(default_factory=list)


class ConfigVersionTestResponse(BaseModel):
    test_status: ConfigVersionTestStatus
    event_id: UUID | None = None
    timeline_url: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
