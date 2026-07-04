from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FlowValidationError(BaseModel):
    step_id: str | None = None
    code: str
    message: str
    hint: str | None = None


class FlowValidationResponse(BaseModel):
    valid: bool
    errors: list[FlowValidationError] = Field(default_factory=list)
    warnings: list[FlowValidationError] = Field(default_factory=list)


class FlowBuilderPreviewRequest(BaseModel):
    builder_json: dict[str, Any]
    sample_request: dict[str, Any] = Field(default_factory=dict)
    run_real_queries: bool = False


class FlowBuilderPreviewStep(BaseModel):
    id: str
    type: str
    name: str | None = None
    status: str
    request_preview: Any | None = None
    result_preview: Any | None = None
    error: dict[str, Any] | None = None


class FlowBuilderPreviewResponse(BaseModel):
    valid: bool
    variables: dict[str, Any] = Field(default_factory=dict)
    steps: list[FlowBuilderPreviewStep] = Field(default_factory=list)
    final_payload_preview: Any | None = None
    target_request_preview: Any | None = None
    errors: list[FlowValidationError] = Field(default_factory=list)


class FlowCompileResponse(BaseModel):
    valid: bool
    workflow_id: str | None = None
    steps_json: list[dict[str, Any]] = Field(default_factory=list)
    validation: FlowValidationResponse
