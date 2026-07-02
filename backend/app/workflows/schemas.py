from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RunStatus
from app.events.schemas import EventRunRead
from app.mappings.schemas import MappingVersionRead

DEFAULT_WORKFLOW_STEPS: list[dict[str, Any]] = [
    {"name": "receive"},
    {"name": "maintenance_guard"},
    {"name": "normalize"},
    {"name": "validate"},
    {"name": "map_payload"},
    {"name": "call_connector"},
    {"name": "handle_response"},
    {"name": "create_incident", "on": "failure"},
    {"name": "send_notifications", "on": "failure"},
]


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    event_type: str | None = None
    source_system: str | None = None
    target_system: str | None = None
    entity_type: str | None = None
    version: int = 1
    enabled: bool = True
    steps_json: list[Any] = Field(default_factory=lambda: list(DEFAULT_WORKFLOW_STEPS))
    validation_json: dict[str, Any] = Field(default_factory=lambda: {"required_fields": ["id", "warehouse.id", "lines"]})
    source_mapping_version_id: UUID | None = None
    target_mapping_version_id: UUID | None = None


class WorkflowPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    event_type: str | None = None
    source_system: str | None = None
    target_system: str | None = None
    entity_type: str | None = None
    version: int | None = None
    enabled: bool | None = None
    steps_json: list[Any] | None = None
    validation_json: dict[str, Any] | None = None
    source_mapping_version_id: UUID | None = None
    target_mapping_version_id: UUID | None = None


class WorkflowRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    event_type: str | None
    source_system: str | None
    target_system: str | None
    entity_type: str | None
    version: int
    enabled: bool
    steps_json: list[Any]
    validation_json: dict[str, Any]
    source_mapping_version_id: UUID | None
    target_mapping_version_id: UUID | None
    source_mapping_version: MappingVersionRead | None = None
    target_mapping_version: MappingVersionRead | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowDryRunRequest(BaseModel):
    payload: dict[str, Any]
    source_system: str | None = None
    target_system: str | None = None
    entity_type: str | None = None


class WorkflowDryRunRead(BaseModel):
    workflow_id: UUID
    workflow_name: str
    status: RunStatus
    run: EventRunRead
