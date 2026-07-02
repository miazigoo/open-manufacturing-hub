from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import PollingCursorType, PollingJobStatus


class PollingJobCreate(BaseModel):
    name: str
    enabled: bool = True
    source_connector_id: UUID
    target_system: str | None = None
    resource: str
    query_json: dict[str, Any] = Field(default_factory=dict)
    event_type: str
    entity_type: str | None = None
    entity_id_field: str | None = "Ref_Key"
    correlation_id_field: str | None = "Number"
    updated_at_field: str | None = "Date"
    cursor_type: PollingCursorType = PollingCursorType.NONE
    interval_seconds: int = 60


class PollingJobPatch(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    target_system: str | None = None
    resource: str | None = None
    query_json: dict[str, Any] | None = None
    event_type: str | None = None
    entity_type: str | None = None
    entity_id_field: str | None = None
    correlation_id_field: str | None = None
    updated_at_field: str | None = None
    cursor_type: PollingCursorType | None = None
    interval_seconds: int | None = None


class PollingJobRead(BaseModel):
    id: UUID
    name: str
    enabled: bool
    source_connector_id: UUID
    target_system: str | None
    resource: str
    query_json: dict[str, Any]
    event_type: str
    entity_type: str | None
    entity_id_field: str | None
    correlation_id_field: str | None
    updated_at_field: str | None
    cursor_value: str | None
    cursor_type: PollingCursorType
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
    items_skipped: int
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None
    details_json: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
