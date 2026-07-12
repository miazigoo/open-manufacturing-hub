from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import PollingCursorType, PollingJobStatus


class PollingJobCreate(BaseModel):
    name: str
    slug: str | None = None
    enabled: bool = True
    source_connector_id: UUID
    integration_flow_id: UUID | None = None
    target_system: str | None = None
    resource: str
    query_json: dict[str, Any] = Field(default_factory=dict)
    config_json: dict[str, Any] = Field(default_factory=dict)
    event_type: str
    entity_type: str | None = None
    entity_id_field: str | None = "Ref_Key"
    correlation_id_field: str | None = "Number"
    updated_at_field: str | None = "Date"
    cursor_json: dict[str, Any] = Field(default_factory=dict)
    cursor_type: PollingCursorType = PollingCursorType.NONE
    schedule_type: str = "interval_minutes"
    interval_seconds: int = 60


class PollingJobPatch(BaseModel):
    name: str | None = None
    slug: str | None = None
    enabled: bool | None = None
    integration_flow_id: UUID | None = None
    target_system: str | None = None
    resource: str | None = None
    query_json: dict[str, Any] | None = None
    config_json: dict[str, Any] | None = None
    event_type: str | None = None
    entity_type: str | None = None
    entity_id_field: str | None = None
    correlation_id_field: str | None = None
    updated_at_field: str | None = None
    cursor_json: dict[str, Any] | None = None
    cursor_type: PollingCursorType | None = None
    schedule_type: str | None = None
    interval_seconds: int | None = None


class PollingJobRead(BaseModel):
    id: UUID
    name: str
    slug: str | None
    enabled: bool
    source_connector_id: UUID
    integration_flow_id: UUID | None
    target_system: str | None
    resource: str
    query_json: dict[str, Any]
    config_json: dict[str, Any]
    event_type: str
    entity_type: str | None
    entity_id_field: str | None
    correlation_id_field: str | None
    updated_at_field: str | None
    cursor_value: str | None
    cursor_json: dict[str, Any]
    cursor_type: PollingCursorType
    schedule_type: str
    interval_seconds: int
    last_run_at: datetime | None
    next_run_at: datetime | None
    status: PollingJobStatus
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PollingJobRunRead(BaseModel):
    id: UUID
    job_id: UUID
    status: PollingJobStatus
    items_read: int
    events_created: int
    sent_count: int
    items_skipped: int
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None
    event_id: UUID | None
    cursor_before_json: dict[str, Any]
    cursor_after_json: dict[str, Any]
    details_json: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PollingRunNowRequest(BaseModel):
    dry_run: bool = False
    update_cursor: bool = True
