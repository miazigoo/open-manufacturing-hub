from __future__ import annotations
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field

class DesignerBuildRequest(BaseModel):
    scenario_code: str
    source: dict[str, Any] = Field(default_factory=dict)
    target: dict[str, Any] = Field(default_factory=dict)
    operation: dict[str, Any] = Field(default_factory=dict)
    logic: dict[str, Any] = Field(default_factory=dict)
    test_payload: Any | None = None

class DesignerCreated(BaseModel):
    endpoint_id: UUID
    route_id: UUID
    workflow_id: UUID
    operation_template_id: UUID | None = None
    test_case_id: UUID | None = None

class DesignerBuildResponse(BaseModel):
    created: DesignerCreated
    endpoint_url: str
    curl_example: str
    onec_http_example: str
    next_steps: list[str]
