from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RunStatus
from app.events.schemas import EventRunRead
from app.mappings.schemas import MappingVersionRead

DEFAULT_WORKFLOW_STEPS = ["receive", "map_to_canonical", "validate", "map_to_target", "send_to_target", "handle_response"]


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    event_type: str
    source_system: str | None = None
    target_system: str | None = None
    entity_type: str | None = None
    version: int = 1
    enabled: bool = True
    steps_json: list[str] = Field(default_factory=lambda: list(DEFAULT_WORKFLOW_STEPS))
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
    steps_json: list[str] | None = None
    validation_json: dict[str, Any] | None = None
    source_mapping_version_id: UUID | None = None
    target_mapping_version_id: UUID | None = None


class WorkflowRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    event_type: str
    source_system: str | None
    target_system: str | None
    entity_type: str | None
    version: int
    enabled: bool
    steps_json: list[str]
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
