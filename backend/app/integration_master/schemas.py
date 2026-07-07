from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

InputMode = Literal["json", "xml", "raw_text"]
OperationKeyType = Literal["field", "endpoint", "none"]


class IntegrationScenario(BaseModel):
    key: str
    title: str
    description: str
    caller: str
    incoming: str
    next_action: str
    source_system: str
    input_modes: list[InputMode]
    default_input_mode: InputMode
    default_slug: str
    sample: Any
    recommended_operation_key: dict[str, Any] = Field(default_factory=dict)
    recommended_business_key: dict[str, Any] = Field(default_factory=dict)


class InputContractField(BaseModel):
    name: str
    path: str
    display_path: str | None = None
    type: str
    required: bool = True
    example: Any = None
    description: str | None = None


class OperationKeySuggestion(BaseModel):
    type: OperationKeyType = "field"
    field_path: str | None = None
    field_name: str | None = None
    value: Any = None
    fallback_paths: list[str] = Field(default_factory=list)
    label: str
    human_text: str
    matcher_json: dict[str, Any] = Field(default_factory=dict)


class BusinessKeySuggestion(BaseModel):
    path: str
    field_name: str
    fallback_paths: list[str] = Field(default_factory=list)
    label: str
    example: Any = None


class InputParseRequest(BaseModel):
    input_mode: InputMode
    sample: Any
    scenario_key: str | None = None


class InputParseResponse(BaseModel):
    input_mode: InputMode
    normalized_sample: Any
    fields: list[InputContractField]
    suggested_operation_keys: list[OperationKeySuggestion]
    suggested_business_keys: list[BusinessKeySuggestion]
    warnings: list[str] = Field(default_factory=list)


class InputOperationKey(BaseModel):
    type: OperationKeyType = "field"
    field_path: str | None = None
    value: Any = None
    fallback_paths: list[str] = Field(default_factory=list)
    matcher_preview: dict[str, Any] = Field(default_factory=dict)


class InputBusinessKey(BaseModel):
    path: str | None = None
    fallback_paths: list[str] = Field(default_factory=list)


class InputContract(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160)
    input_mode: InputMode
    source_system: str = "external_api"
    scenario_key: str | None = None
    sample: Any
    fields: list[InputContractField] = Field(default_factory=list)
    operation_key: InputOperationKey = Field(default_factory=InputOperationKey)
    business_key: InputBusinessKey = Field(default_factory=InputBusinessKey)
    endpoint_url: str | None = None


class InputContractValidationRequest(BaseModel):
    contract: InputContract


class InputContractValidationResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    endpoint_url: str
    matcher_preview: dict[str, Any] = Field(default_factory=dict)


class InputDraftSaveRequest(BaseModel):
    contract: InputContract
    parse_result: InputParseResponse | None = None


class InputDraftRead(BaseModel):
    id: UUID
    name: str
    slug: str
    scenario_key: str | None = None
    input_mode: InputMode
    source_system: str
    contract: InputContract
    parse_result: InputParseResponse | None = None
    endpoint_url: str
    created_at: datetime
    updated_at: datetime


class InputDraftSaveResponse(BaseModel):
    draft: InputDraftRead
    next_steps: list[str]
