from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.artifacts.schemas import ArtifactRead
from app.core.enums import EventStatus, RunMode, RunStatus, StepStatus


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


class EventStepRead(BaseModel):
    id: UUID
    step_order: int
    step_name: str
    status: StepStatus
    error_code: str | None
    error_message: str | None
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
