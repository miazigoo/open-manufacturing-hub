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
ForeachODataMergeMode = Literal["flatten", "group_by_item", "first_per_item"]
PayloadBodyType = Literal["json", "xml", "raw_text"]
JsonPayloadMode = Literal["table", "raw_template"]
JsonPayloadValueType = Literal[
    "variable",
    "template_string",
    "constant_string",
    "constant_number",
    "constant_boolean",
    "constant_null",
    "object",
    "array",
]


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


class ForeachODataSafetyLimits(BaseModel):
    max_items: int = 100
    max_requests: int = 100
    max_result_rows: int = 10000


class ForeachODataStepConfig(BaseModel):
    id: str | None = None
    type: Literal["foreach_odata"] = "foreach_odata"
    items: str = "products"
    item_as: str = "product"
    connection_id: UUID | None = None
    connection_name: str | None = None
    resource: str = "InformationRegister_ПулКодовМаркировкиСУЗ"
    filter: str | None = None
    select: list[str] = Field(default_factory=list)
    top: int | None = 500
    paginate: bool = True
    merge: ForeachODataMergeMode = "flatten"
    save_as: str = "codes"
    required: bool = True
    limits: ForeachODataSafetyLimits = Field(default_factory=ForeachODataSafetyLimits)
    test_limit: int | None = 1
    overwrite: bool = False
    last_test_status: str | None = None


class JsonPayloadFieldConfig(BaseModel):
    target_path: str = ""
    value_source: Any = None
    value_type: JsonPayloadValueType = "variable"


class JsonPayloadDynamicEntryConfig(BaseModel):
    object_path: str = ""
    key_source: str = ""
    value_source: Any = None
    value_type: JsonPayloadValueType = "variable"


class PayloadStepConfig(BaseModel):
    id: str | None = None
    type: Literal["build_payload"] = "build_payload"
    body_type: PayloadBodyType = "json"
    save_as: str = "target_payload"
    json_mode: JsonPayloadMode = "table"
    template: Any = None
    fields: list[JsonPayloadFieldConfig] = Field(default_factory=list)
    dynamic_entries: list[JsonPayloadDynamicEntryConfig] = Field(default_factory=list)
    overwrite: bool = False
    last_preview_status: str | None = None


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


class ForeachODataStepRequest(BaseModel):
    input_contract: InputContract
    previous_variables: dict[str, Any] = Field(default_factory=dict)
    foreach_step: ForeachODataStepConfig


class PayloadStepRequest(BaseModel):
    input_contract: InputContract | None = None
    previous_variables: dict[str, Any] = Field(default_factory=dict)
    payload_step: PayloadStepConfig


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


class ForeachODataStepValidationResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_count: int = 0
    first_item_preview: dict[str, Any] | None = None
    template_filter: str | None = None
    rendered_filter: str | None = None
    template_url: str | None = None
    rendered_url: str | None = None
    variables_after_step: list[str] = Field(default_factory=list)


class ForeachODataStepPreviewResponse(ForeachODataStepValidationResponse):
    saved_as: str
    items: str
    item_as: str
    merge: ForeachODataMergeMode


class PayloadStepValidationResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    body_type: PayloadBodyType
    save_as: str
    error_code: str | None = None
    variables_after_step: list[str] = Field(default_factory=list)


class PayloadStepPreviewResponse(PayloadStepValidationResponse):
    rendered_preview: Any = None
    size_bytes: int = 0


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


class ForeachODataStepTestResponse(BaseModel):
    success: bool
    error_code: str | None = None
    message: str | None = None
    hint: str | None = None
    source_count: int = 0
    items_processed: int = 0
    odata_requests: int = 0
    rows_found: int = 0
    merge: ForeachODataMergeMode = "flatten"
    saved_as: str
    result_preview: Any = None
    variables_after_step: list[str] = Field(default_factory=list)
    requests: list[dict[str, Any]] = Field(default_factory=list)


class ODataStepSaveRequest(BaseModel):
    input_contract: InputContract | None = None
    odata_step: ODataStepConfig


class ODataObjectStepSaveRequest(BaseModel):
    input_contract: InputContract | None = None
    previous_variables: dict[str, Any] = Field(default_factory=dict)
    odata_object_step: ODataObjectStepConfig


class ForeachODataStepSaveRequest(BaseModel):
    input_contract: InputContract | None = None
    previous_variables: dict[str, Any] = Field(default_factory=dict)
    foreach_step: ForeachODataStepConfig


class PayloadStepSaveRequest(BaseModel):
    input_contract: InputContract | None = None
    previous_variables: dict[str, Any] = Field(default_factory=dict)
    payload_step: PayloadStepConfig


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
    odata_steps: list[ODataStepConfig | ODataObjectStepConfig | ForeachODataStepConfig | PayloadStepConfig] = Field(default_factory=list)
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


class ForeachODataStepSaveResponse(BaseModel):
    draft: InputDraftRead
    saved_step: ForeachODataStepConfig
    next_steps: list[str]


class PayloadStepSaveResponse(BaseModel):
    draft: InputDraftRead
    saved_step: PayloadStepConfig
    next_steps: list[str]


class InputDraftSaveResponse(BaseModel):
    draft: InputDraftRead
    next_steps: list[str]
