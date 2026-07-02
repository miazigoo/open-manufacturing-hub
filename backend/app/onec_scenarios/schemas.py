from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OneCScenarioPresetRead(BaseModel):
    key: str
    name: str
    description: str
    source_resource: str
    event_type: str
    entity_type: str
    mappings: list[str]


class OneCScenarioInstallRead(BaseModel):
    scenario: str
    source_connector_id: UUID
    target_connector_id: UUID
    workflow_id: UUID
    polling_job_id: UUID
    mappings: list[str]
    notes: list[str]

    model_config = ConfigDict(from_attributes=True)
