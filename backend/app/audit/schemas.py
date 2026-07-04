from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AuditActorType, AuditSeverity


class AuditEventRead(BaseModel):
    id: UUID
    timestamp: datetime
    actor_user_id: UUID | None
    actor_username: str | None
    actor_display_name: str | None
    actor_type: AuditActorType
    source_ip: str | None
    user_agent: str | None
    action: str
    category: str
    severity: AuditSeverity
    object_type: str | None
    object_id: str | None
    object_name: str | None
    summary: str
    details_json: dict[str, Any] | None
    before_json: dict[str, Any] | None
    after_json: dict[str, Any] | None
    diff_json: dict[str, Any] | None
    request_id: str | None
    correlation_id: str | None
    event_id: UUID | None
    queue_item_id: UUID | None
    package_id: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditListResponse(BaseModel):
    items: list[AuditEventRead]
    total: int
    limit: int
    offset: int


class AuditCleanupRequest(BaseModel):
    retention_days: int | None = Field(default=None, ge=1, le=3650)
    dry_run: bool = False


class AuditCleanupResponse(BaseModel):
    retention_days: int
    cutoff: datetime
    deleted: int
    dry_run: bool


class AuditStats(BaseModel):
    total: int
    by_category: dict[str, int]
    by_severity: dict[str, int]
    oldest_timestamp: datetime | None
    newest_timestamp: datetime | None
