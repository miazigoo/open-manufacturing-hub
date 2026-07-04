from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.artifacts.schemas import ArtifactRead
from app.core.enums import EventStatus, RunMode, RunStatus, StepStatus
from app.external_errors.schemas import ExternalErrorSummary


class EventCreate(BaseModel):
    correlation_id: str | None = None
    source_system: str
    target_system: str | None = None
    event_type: str
    entity_type: str | None = None
    entity_id: str | None = None
    payload: dict[str, Any]


class EventSummary(BaseModel):
    id: UUID
    correlation_id: str | None
    source_system: str
    target_system: str | None
    event_type: str
    entity_type: str | None
    entity_id: str | None
    status: EventStatus
    pinned: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventQueueInfo(BaseModel):
    id: UUID
    status: str
    attempts: int
    max_attempts: int
    next_retry_at: datetime | None = None
    locked_by: str | None = None
    locked_until: datetime | None = None
    last_error: str | None = None
    timeline_link: str | None = None


class EventStepRead(BaseModel):
    id: UUID
    step_order: int
    step_name: str
    status: StepStatus
    error_code: str | None
    error_message: str | None
    human_title: str | None = None
    human_summary: str | None = None
    developer_message: str | None = None
    hint: str | None = None
    external_error_record_id: UUID | None = None
    external_error: ExternalErrorSummary | None = None
    step_config_json: dict[str, Any]
    condition: str | None
    artifacts: list[ArtifactRead] = []

    model_config = ConfigDict(from_attributes=True)


class EventRunRead(BaseModel):
    id: UUID
    event_id: UUID
    run_number: int
    mode: RunMode
    status: RunStatus
    parent_run_id: UUID | None
    workflow_id: UUID | None
    workflow_name: str | None
    workflow_version: int | None
    mapping_versions_json: dict[str, Any]
    started_at: datetime | None
    finished_at: datetime | None
    steps: list[EventStepRead] = []
    artifacts: list[ArtifactRead] = []

    model_config = ConfigDict(from_attributes=True)


class EventTimeline(BaseModel):
    event: EventSummary
    runs: list[EventRunRead]
    queue_item: EventQueueInfo | None = None


class EventJournalItem(BaseModel):
    id: UUID
    correlation_id: str | None
    source_system: str
    target_system: str | None
    event_type: str
    entity_type: str | None
    entity_id: str | None
    status: EventStatus
    pinned: bool
    created_at: datetime
    human_title: str
    human_summary: str
    business_key: str | None = None
    operation: str | None = None
    document_type: str | None = None
    document_number: str | None = None
    source_display: str | None = None
    target_display: str | None = None
    last_step: str | None = None
    last_error_code: str | None = None
    last_error_summary: str | None = None
    last_external_error_message: str | None = None
    hint: str | None = None
    requires_attention: bool = False
    queue_status: str | None = None
    queue_attempts: int | None = None
    queue_max_attempts: int | None = None
    queue_next_retry_at: datetime | None = None
