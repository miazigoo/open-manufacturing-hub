from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import IncidentSeverity, IncidentStatus
from app.external_errors.schemas import ExternalErrorSummary


class IncidentRead(BaseModel):
    id: UUID
    fingerprint: str
    title: str
    status: IncidentStatus
    severity: IncidentSeverity
    source_system: str | None
    target_system: str | None
    failed_step: str | None
    error_code: str | None
    normalized_error_message: str | None
    affected_events_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    sample_external_errors: list[ExternalErrorSummary] = []

    model_config = ConfigDict(from_attributes=True)


class IncidentEventRead(BaseModel):
    id: UUID
    incident_id: UUID
    event_id: UUID
    run_id: UUID | None
    step_id: UUID | None
    event_type: str | None = None
    event_status: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
