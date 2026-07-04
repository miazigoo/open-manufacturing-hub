from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ScenarioRead(BaseModel):
    code: str
    title: str
    description: str
    source: str
    target: str
    input_modes: list[str]
    default_slug: str
    event_type: str
    entity_type: str | None = None
    operation_code: str
    sample_payload: Any


class ScenarioObjectPreview(BaseModel):
    type: str
    name: str


class ScenarioPreview(BaseModel):
    scenario: str
    will_create: dict[str, int]
    objects: list[ScenarioObjectPreview]


class ScenarioInstallRequest(BaseModel):
    endpoint_slug: str | None = None
    endpoint_name: str | None = None
    source_system: str | None = None
    target_system: str | None = None
    target_connector_id: UUID | None = None
    response_mode: str = "sync_response"
    input_mode: str | None = None
    auth_mode: str = "none"
    auth_config_json: dict[str, Any] = Field(default_factory=dict)
    create_test_case: bool = True


class ScenarioInstallResponse(BaseModel):
    scenario: str
    endpoint_id: UUID
    route_id: UUID
    workflow_id: UUID
    operation_template_id: UUID | None = None
    test_case_id: UUID | None = None
    endpoint_url: str
    curl_example: str
    onec_http_example: str
    next_steps: list[str]
