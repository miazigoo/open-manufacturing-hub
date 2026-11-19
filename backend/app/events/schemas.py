from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.artifacts.schemas import ArtifactRead, ArtifactSummary
from app.core.enums import EventStatus, RunMode, RunStatus, StepStatus
from app.core.pagination import PageResponse
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


class EventStepSummary(BaseModel):
    id: UUID
    step_order: int
    step_name: str
    status: StepStatus
    error_code: str | None = None
    error_message: str | None = None
    human_title: str | None = None
    human_summary: str | None = None
    developer_message: str | None = None
    hint: str | None = None
    external_error_record_id: UUID | None = None
    external_error: ExternalErrorSummary | None = None
    condition: str | None = None
    artifacts: list[ArtifactSummary] = []

    model_config = ConfigDict(from_attributes=True)


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


class EventRunSummary(BaseModel):
    id: UUID
    event_id: UUID
    run_number: int
    mode: RunMode
    status: RunStatus
    parent_run_id: UUID | None = None
    workflow_id: UUID | None = None
    workflow_name: str | None = None
    workflow_version: int | None = None
    mapping_versions_json: dict[str, Any] = {}
    started_at: datetime | None = None
    finished_at: datetime | None = None
    steps: list[EventStepSummary] = []
    artifacts: list[ArtifactSummary] = []

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


class EventOverview(BaseModel):
    event: EventSummary
    queue_item: EventQueueInfo | None = None
    runs: list[EventRunSummary] = []
    has_more_runs: bool = False
    next_runs_cursor: str | None = None


class EventDashboardSummary(BaseModel):
    timezone: str = "UTC"
    period_start: datetime
    period_end: datetime
    events_today: int = 0
    failed_today: int = 0
    retry_waiting: int = 0
    open_incidents: int = 0
    queue_backlog: int = 0
    queue_processing: int = 0
    latest_failures: list[EventSummary] = []


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


class EventJournalPageResponse(PageResponse[EventJournalItem]):
    pass
