from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

InputMode = Literal["json", "xml", "raw_text"]
OperationKeyType = Literal["field", "endpoint", "none"]
ODataFilterMode = Literal["builder", "raw"]
ODataFilterOperator = Literal["eq", "ne", "contains", "gt", "lt", "ge", "le"]
ODataValueType = Literal["string", "number", "boolean", "variable", "guid", "raw"]
ODataObjectKeyType = Literal["guid", "string", "number", "raw"]


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


class ODataFilterRule(BaseModel):
    field: str = ""
    operator: ODataFilterOperator = "eq"
    value_type: ODataValueType = "variable"
    value: Any = None


class ODataStepConfig(BaseModel):
    id: str | None = None
    type: Literal["odata_query"] = "odata_query"
    connection_id: UUID | None = None
    connection_name: str | None = None
    resource: str = ""
    filter_mode: ODataFilterMode = "builder"
    filter_rule: ODataFilterRule | None = None
    filter: str | None = None
    select: list[str] = Field(default_factory=list)
    top: int | None = 1
    orderby: str | None = None
    paginate: bool = False
    save_as: str = "order"
    required: bool = True
    last_test_status: str | None = None


class ODataObjectStepConfig(BaseModel):
    id: str | None = None
    type: Literal["odata_object_query"] = "odata_object_query"
    connection_id: UUID | None = None
    connection_name: str | None = None
    object_variable: str = ""
    key_field: str = "Ref_Key"
    key_type: ODataObjectKeyType = "guid"
    base_resource: str = ""
    nested_resource: str = ""
    resource_template: str | None = None
    filter: str | None = None
    select: list[str] = Field(default_factory=list)
    top: int | None = 100
    paginate: bool = False
    save_as: str = "products"
    required: bool = True
    overwrite: bool = False
    last_test_status: str | None = None


class ResourceRenderResult(BaseModel):
    template_resource: str
    rendered_resource: str | None = None


class ODataStepRequest(BaseModel):
    input_contract: InputContract
    sample_input: Any = None
    odata_step: ODataStepConfig


class ODataObjectStepRequest(BaseModel):
    input_contract: InputContract
    previous_variables: dict[str, Any] = Field(default_factory=dict)
    odata_object_step: ODataObjectStepConfig


class ODataStepValidationResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    template_filter: str | None = None
    rendered_filter: str | None = None
    template_url: str | None = None
    rendered_url: str | None = None
    variables_after_step: list[str] = Field(default_factory=list)


class ODataStepPreviewResponse(ODataStepValidationResponse):
    rendered_resource: str
    saved_as: str


class ODataObjectStepValidationResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    template_resource: str | None = None
    rendered_resource: str | None = None
    template_filter: str | None = None
    rendered_filter: str | None = None
    template_url: str | None = None
    rendered_url: str | None = None
    variables_after_step: list[str] = Field(default_factory=list)


class ODataObjectStepPreviewResponse(ODataObjectStepValidationResponse):
    saved_as: str
    object_variable: str
    key_preview: Any = None


class ODataStepTestResponse(BaseModel):
    success: bool
    error_code: str | None = None
    message: str | None = None
    hint: str | None = None
    rendered_resource: str
    rendered_filter: str | None = None
    items_count: int = 0
    result_preview: dict[str, Any] | None = None
    saved_as: str
    variables_after_step: list[str] = Field(default_factory=list)
    request: dict[str, Any] = Field(default_factory=dict)


class ODataObjectStepTestResponse(BaseModel):
    success: bool
    error_code: str | None = None
    message: str | None = None
    hint: str | None = None
    rendered_resource: str
    rendered_filter: str | None = None
    items_count: int = 0
    result_preview: list[dict[str, Any]] = Field(default_factory=list)
    saved_as: str
    variables_after_step: list[str] = Field(default_factory=list)
    request: dict[str, Any] = Field(default_factory=dict)


class ODataStepSaveRequest(BaseModel):
    input_contract: InputContract | None = None
    odata_step: ODataStepConfig


class ODataObjectStepSaveRequest(BaseModel):
    input_contract: InputContract | None = None
    previous_variables: dict[str, Any] = Field(default_factory=dict)
    odata_object_step: ODataObjectStepConfig


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
    odata_steps: list[ODataStepConfig | ODataObjectStepConfig] = Field(default_factory=list)
    parse_result: InputParseResponse | None = None
    endpoint_url: str
    created_at: datetime
    updated_at: datetime


class ODataStepSaveResponse(BaseModel):
    draft: InputDraftRead
    saved_step: ODataStepConfig
    next_steps: list[str]


class ODataObjectStepSaveResponse(BaseModel):
    draft: InputDraftRead
    saved_step: ODataObjectStepConfig
    next_steps: list[str]


class InputDraftSaveResponse(BaseModel):
    draft: InputDraftRead
    next_steps: list[str]
