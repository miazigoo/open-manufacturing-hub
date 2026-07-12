from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.integration_master.schemas import (
    CompileDraftResponse,
    CompiledRunTestResponse,
    FinalActionBodySource,
    FinalActionBodyType,
    FinalActionMethod,
    FinalActionReturnType,
    ForeachODataStepConfig,
    InputContract,
    ODataObjectStepConfig,
    ODataStepConfig,
    PayloadBodyType,
    PayloadStepConfig,
)

LocalizedText = dict[str, str]
PatternCategory = Literal[
    "request_response",
    "odata",
    "file_exchange",
    "xml",
    "printing",
    "polling",
    "writeback",
]
PatternDifficulty = Literal["basic", "intermediate", "advanced"]
PatternStatus = Literal["available", "coming_soon"]
InputMode = Literal["json", "xml", "raw_text", "file", "odata"]
PatternCertificationStatus = Literal[
    "not_started",
    "partial",
    "ready_for_training",
    "ready_for_production",
    "deprecated",
]
PatternCertificationCheckStatus = Literal["passed", "warning", "failed", "planned"]


class IntegrationPattern(BaseModel):
    pattern_id: str
    title: LocalizedText
    description: LocalizedText
    category: PatternCategory
    difficulty: PatternDifficulty
    status: PatternStatus = "available"
    input_modes: list[InputMode]
    data_steps: list[str]
    final_actions: list[str]
    recommended_wizard: str
    wizard_route: str | None = None
    wizard_label: LocalizedText = Field(default_factory=dict)
    examples: list[str] = Field(default_factory=list)
    package_requirements: list[str] = Field(default_factory=list)
    docs_link: str
    use_cases: list[LocalizedText] = Field(default_factory=list)
    flow: list[str] = Field(default_factory=list)
    initial_steps: list[str] = Field(default_factory=list)
    required_inputs: list[LocalizedText] = Field(default_factory=list)
    expected_result: LocalizedText = Field(default_factory=dict)
    test_plan: list[LocalizedText] = Field(default_factory=list)
    timeline_hint: LocalizedText = Field(default_factory=dict)
    start_disabled_reason: LocalizedText | None = None


class PatternRecommendRequest(BaseModel):
    source_system: str | None = None
    input_mode: InputMode | None = None
    needs_odata: bool | None = None
    needs_foreach: bool | None = None
    needs_file_save: bool | None = None
    needs_response: bool | None = None
    needs_send_endpoint: bool | None = None
    needs_print: bool | None = None
    needs_writeback: bool | None = None
    needs_polling: bool | None = None


class PatternRecommendation(BaseModel):
    pattern_id: str
    confidence: float
    reason: str
    pattern: IntegrationPattern


class PatternRecommendResponse(BaseModel):
    recommended_patterns: list[PatternRecommendation]


class PatternStartRequest(BaseModel):
    pattern_id: str


class PatternStartResponse(BaseModel):
    pattern_id: str
    wizard_route: str
    recommended_wizard: str
    wizard_label: LocalizedText = Field(default_factory=dict)
    initial_steps: list[str]
    explanation: LocalizedText = Field(default_factory=dict)
    examples: list[str] = Field(default_factory=list)
    package_requirements: list[str] = Field(default_factory=list)


class PatternCertificationCheck(BaseModel):
    key: str
    label: LocalizedText
    status: PatternCertificationCheckStatus
    message: LocalizedText
    link: str | None = None
    source: str = "pattern_certification"


class PatternCertification(BaseModel):
    pattern_id: str
    title: LocalizedText
    description: LocalizedText
    certification_status: PatternCertificationStatus
    status_label: LocalizedText
    wizard_route: str | None = None
    docs_link: str | None = None
    coverage_requirement_ids: list[str] = Field(default_factory=list)
    ui_status: PatternCertificationCheckStatus
    docs_status: PatternCertificationCheckStatus
    training_status: PatternCertificationCheckStatus
    tests_status: PatternCertificationCheckStatus
    timeline_status: PatternCertificationCheckStatus
    simple_mode_status: PatternCertificationCheckStatus
    checks: list[PatternCertificationCheck] = Field(default_factory=list)
    problems: list[str] = Field(default_factory=list)
    actions: list[LocalizedText] = Field(default_factory=list)


class PatternCertificationSummary(BaseModel):
    total: int
    not_started: int = 0
    partial: int = 0
    ready_for_training: int = 0
    ready_for_production: int = 0
    deprecated: int = 0
    problem_patterns: int = 0


class PatternCertificationListResponse(BaseModel):
    summary: PatternCertificationSummary
    items: list[PatternCertification]


class RequestODataResponseResponseConfig(BaseModel):
    type: PayloadBodyType = "json"
    status_code: int = Field(default=200, ge=100, le=599)
    body: Any = Field(default_factory=dict)
    headers: dict[str, Any] = Field(default_factory=dict)


class RequestODataResponsePatternRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160)
    input_contract: InputContract
    odata_step: ODataStepConfig
    response: RequestODataResponseResponseConfig = Field(default_factory=RequestODataResponseResponseConfig)


class RequestODataResponsePreviewResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    endpoint: dict[str, Any] = Field(default_factory=dict)
    incoming_request: Any = None
    odata_request: dict[str, Any] = Field(default_factory=dict)
    odata_result: dict[str, Any] | None = None
    response_to_caller: Any = None
    human_steps: list[str] = Field(default_factory=list)
    advanced: dict[str, Any] = Field(default_factory=dict)


class RequestODataResponseCreateResponse(BaseModel):
    draft_id: UUID
    compile: CompileDraftResponse
    preview: RequestODataResponsePreviewResponse


class RequestODataResponseRunTestRequest(BaseModel):
    integration_flow_id: UUID
    dry_run: bool = True


class RequestODataResponseRunTestResponse(CompiledRunTestResponse):
    pass


class RequestMultipleODataResponseResponseConfig(BaseModel):
    type: PayloadBodyType = "xml"
    status_code: int = Field(default=200, ge=100, le=599)
    template: Any = ""
    headers: dict[str, Any] = Field(default_factory=dict)


class RequestMultipleODataResponsePatternRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160)
    input_contract: InputContract
    find_order: ODataStepConfig
    read_items: ODataObjectStepConfig
    response: RequestMultipleODataResponseResponseConfig = Field(default_factory=RequestMultipleODataResponseResponseConfig)


class RequestMultipleODataResponsePreviewResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    endpoint: dict[str, Any] = Field(default_factory=dict)
    incoming_request: Any = None
    order_request: dict[str, Any] = Field(default_factory=dict)
    order_result: dict[str, Any] | None = None
    items_request: dict[str, Any] = Field(default_factory=dict)
    items_result: list[dict[str, Any]] = Field(default_factory=list)
    response_to_caller: Any = None
    human_steps: list[str] = Field(default_factory=list)
    advanced: dict[str, Any] = Field(default_factory=dict)


class RequestMultipleODataResponseCreateResponse(BaseModel):
    draft_id: UUID
    compile: CompileDraftResponse
    preview: RequestMultipleODataResponsePreviewResponse


class RequestMultipleODataResponseRunTestRequest(BaseModel):
    integration_flow_id: UUID
    dry_run: bool = True


class RequestMultipleODataResponseRunTestResponse(CompiledRunTestResponse):
    pass


class RequestODataSendEndpointTargetConfig(BaseModel):
    operation_id: UUID | None = None
    operation_code: str | None = None
    operation_name: str | None = None
    method: FinalActionMethod = "POST"
    url: str = ""
    headers: dict[str, Any] = Field(default_factory=lambda: {"Content-Type": "application/json"})
    body_source: FinalActionBodySource = "target_payload"
    body_type: FinalActionBodyType = "json"
    custom_body: Any = None
    timeout_seconds: int = Field(default=20, ge=1, le=300)


class RequestODataSendEndpointResponseConfig(BaseModel):
    type: FinalActionReturnType = "proxy_response"
    status_code: int = Field(default=200, ge=100, le=599)
    body: Any = None
    headers: dict[str, Any] = Field(default_factory=dict)


class RequestODataSendEndpointPatternRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160)
    input_contract: InputContract
    odata_step: ODataStepConfig
    payload: PayloadStepConfig
    target: RequestODataSendEndpointTargetConfig = Field(default_factory=RequestODataSendEndpointTargetConfig)
    response_to_caller: RequestODataSendEndpointResponseConfig = Field(default_factory=RequestODataSendEndpointResponseConfig)


class RequestODataSendEndpointPreviewResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    endpoint: dict[str, Any] = Field(default_factory=dict)
    incoming_request: Any = None
    odata_request: dict[str, Any] = Field(default_factory=dict)
    odata_result: dict[str, Any] | None = None
    target_payload: Any = None
    target_request: dict[str, Any] | None = None
    response_to_caller: Any = None
    human_steps: list[str] = Field(default_factory=list)
    advanced: dict[str, Any] = Field(default_factory=dict)


class RequestODataSendEndpointCreateResponse(BaseModel):
    draft_id: UUID
    compile: CompileDraftResponse
    preview: RequestODataSendEndpointPreviewResponse


class RequestODataSendEndpointRunTestRequest(BaseModel):
    integration_flow_id: UUID
    dry_run: bool = True


class RequestODataSendEndpointRunTestResponse(CompiledRunTestResponse):
    pass


class RequestODataObjectForeachSendEndpointPatternRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160)
    input_contract: InputContract
    find_order: ODataStepConfig
    read_products: ODataObjectStepConfig
    find_codes: ForeachODataStepConfig
    payload: PayloadStepConfig
    target: RequestODataSendEndpointTargetConfig = Field(default_factory=RequestODataSendEndpointTargetConfig)
    response_to_caller: RequestODataSendEndpointResponseConfig = Field(
        default_factory=lambda: RequestODataSendEndpointResponseConfig(
            type="fixed_success",
            status_code=200,
            body={"ok": True},
            headers={"Content-Type": "application/json"},
        )
    )


class RequestODataObjectForeachSendEndpointPreviewResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    endpoint: dict[str, Any] = Field(default_factory=dict)
    incoming_request: Any = None
    order_request: dict[str, Any] = Field(default_factory=dict)
    order_result: dict[str, Any] | None = None
    products_request: dict[str, Any] = Field(default_factory=dict)
    products_result: list[dict[str, Any]] = Field(default_factory=list)
    codes_requests: list[dict[str, Any]] = Field(default_factory=list)
    codes_result: Any = None
    codes_summary: dict[str, Any] = Field(default_factory=dict)
    target_payload: Any = None
    target_request: dict[str, Any] | None = None
    response_to_caller: Any = None
    human_steps: list[str] = Field(default_factory=list)
    advanced: dict[str, Any] = Field(default_factory=dict)


class RequestODataObjectForeachSendEndpointCreateResponse(BaseModel):
    draft_id: UUID
    compile: CompileDraftResponse
    preview: RequestODataObjectForeachSendEndpointPreviewResponse


class RequestODataObjectForeachSendEndpointRunTestRequest(BaseModel):
    integration_flow_id: UUID
    dry_run: bool = True


class RequestODataObjectForeachSendEndpointRunTestResponse(CompiledRunTestResponse):
    pass


class PollODataJobBasicsConfig(BaseModel):
    name: str = Field(default="Sync 1C orders to WMS", min_length=1, max_length=255)
    slug: str = Field(default="sync-1c-orders-to-wms", min_length=1, max_length=160)
    enabled_after_create: bool = False
    schedule_type: Literal["manual_only", "interval_minutes"] = "manual_only"
    interval_minutes: int = Field(default=5, ge=1, le=1440)


class PollODataFirstRunStrategyConfig(BaseModel):
    strategy: Literal["fixed_start_date", "last_n_hours", "no_cursor_filter"] = "fixed_start_date"
    fixed_start_at: str = "2026-01-01T00:00:00"
    hours: int = Field(default=24, ge=1, le=8760)


class PollODataCursorConfig(BaseModel):
    cursor_type: Literal["last_success_at", "field_max_value", "manual"] = "last_success_at"
    source_field: str = "orders[].Date"
    update_when: Literal["target_success", "odata_success", "manual"] = "target_success"


class PollODataTargetConfig(BaseModel):
    operation_id: UUID | None = None
    operation_code: str | None = None
    operation_name: str | None = None
    method: FinalActionMethod = "POST"
    url: str = "http://wms.local/api/orders/import"
    headers: dict[str, Any] = Field(default_factory=lambda: {"Content-Type": "application/json"})
    body_source: str = "target_payload"
    body_type: FinalActionBodyType = "json"
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    empty_result_behavior: Literal["do_nothing_success", "send_empty_payload", "mark_warning"] = "do_nothing_success"


class PollODataSendTargetPatternRequest(BaseModel):
    job: PollODataJobBasicsConfig = Field(default_factory=PollODataJobBasicsConfig)
    odata_step: ODataStepConfig = Field(default_factory=lambda: ODataStepConfig(
        connection_name="Training OData ERP",
        resource="Document_ЗаказКлиента",
        filter_mode="raw",
        filter="Date ge datetime'{{cursor.last_success_at}}' and Posted eq true",
        select=["Ref_Key", "Number", "Date", "Posted", "Контрагент_Key"],
        top=100,
        paginate=True,
        save_as="orders",
        required=False,
    ))
    first_run: PollODataFirstRunStrategyConfig = Field(default_factory=PollODataFirstRunStrategyConfig)
    cursor: PollODataCursorConfig = Field(default_factory=PollODataCursorConfig)
    payload: PayloadStepConfig = Field(default_factory=lambda: PayloadStepConfig(
        body_type="json",
        save_as="target_payload",
        json_mode="raw_template",
        template={
            "omh": {
                "run_id": "{{context.run_id}}",
                "event_type": "ODataPollingOrders",
                "source_system": "1C ERP",
                "target_system": "WMS",
            },
            "payload": {
                "orders": "{{orders}}",
                "cursor_from": "{{cursor.last_success_at}}",
                "count": "{{orders.length}}",
            },
        },
        overwrite=True,
    ))
    target: PollODataTargetConfig = Field(default_factory=PollODataTargetConfig)


class PollODataSendTargetPreviewResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    schedule: dict[str, Any] = Field(default_factory=dict)
    odata_request: dict[str, Any] = Field(default_factory=dict)
    first_run_filter: str = ""
    odata_result: list[dict[str, Any]] = Field(default_factory=list)
    target_payload: Any = None
    target_request: dict[str, Any] | None = None
    cursor: dict[str, Any] = Field(default_factory=dict)
    run_history_hint: dict[str, Any] = Field(default_factory=dict)
    human_steps: list[str] = Field(default_factory=list)
    advanced: dict[str, Any] = Field(default_factory=dict)


class PollODataSendTargetCreateResponse(BaseModel):
    polling_job_id: UUID
    integration_flow_id: UUID | None = None
    preview: PollODataSendTargetPreviewResponse
    run_now_url: str
    runs_url: str
    enabled: bool
    next_steps: list[str] = Field(default_factory=list)


class PollODataSendTargetRunTestRequest(BaseModel):
    pattern: PollODataSendTargetPatternRequest | None = None
    polling_job_id: UUID | None = None
    dry_run: bool = True
    update_cursor: bool = False


class PollODataSendTargetRunTestResponse(BaseModel):
    success: bool
    run: dict[str, Any]
    preview: PollODataSendTargetPreviewResponse | None = None


class SourceWebApiWritebackEndpointConfig(BaseModel):
    operation_id: UUID | None = None
    operation_code: str | None = None
    operation_name: str | None = None
    method: FinalActionMethod = "POST"
    url: str = ""
    headers: dict[str, Any] = Field(default_factory=lambda: {"Content-Type": "application/json"})
    body_source: str = "site_payload"
    body_type: FinalActionBodyType = "json"
    custom_body: Any = None
    timeout_seconds: int = Field(default=20, ge=1, le=300)
    save_response_as: str = "site_response"
    mock_response_json: Any = None


class SourceWebApiWritebackSuccessCondition(BaseModel):
    path: str = "site_response.success"
    operator: Literal["eq", "ne"] = "eq"
    value: Any = True


class SourceWebApiWritebackExtractionConfig(BaseModel):
    external_id_path: str = "site_response.external_id"
    status_path: str = "site_response.status"
    success_condition: SourceWebApiWritebackSuccessCondition = Field(default_factory=SourceWebApiWritebackSuccessCondition)
    sample_response: dict[str, Any] = Field(default_factory=lambda: {"success": True, "external_id": "SITE-ORDER-123", "status": "accepted"})


class SourceWebApiWritebackOneCServiceConfig(BaseModel):
    operation_id: UUID | None = None
    operation_code: str | None = None
    operation_name: str | None = None
    method: FinalActionMethod = "POST"
    connector_id: UUID | None = None
    connector_name: str | None = None
    base_url: str = "http://1c-server/erp/hs/omh"
    path: str = "/order-external-id"
    url: str = ""
    headers: dict[str, Any] = Field(default_factory=lambda: {"Content-Type": "application/json"})
    body_source: str = "onec_writeback_payload"
    body_type: FinalActionBodyType = "json"
    timeout_seconds: int = Field(default=20, ge=1, le=300)
    save_response_as: str = "onec_writeback_response"
    mock_response_json: Any = None


class SourceWebApiWritebackCallerResponseConfig(BaseModel):
    type: Literal["custom_json", "site_response", "onec_writeback_response", "accepted_event"] = "custom_json"
    status_code: int = Field(default=200, ge=100, le=599)
    body: Any = Field(
        default_factory=lambda: {
            "success": True,
            "order_number": "{{order.Number}}",
            "external_id": "{{site_response.external_id}}",
            "site_status": "{{site_response.status}}",
            "onec_writeback_success": "{{onec_writeback_response.success}}",
        }
    )
    headers: dict[str, Any] = Field(default_factory=lambda: {"Content-Type": "application/json"})


class SourceWebApiWritebackOneCPatternRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160)
    input_contract: InputContract
    odata_step: ODataStepConfig
    site_payload: PayloadStepConfig
    site_endpoint: SourceWebApiWritebackEndpointConfig = Field(default_factory=SourceWebApiWritebackEndpointConfig)
    site_response_extraction: SourceWebApiWritebackExtractionConfig = Field(default_factory=SourceWebApiWritebackExtractionConfig)
    onec_writeback_payload: PayloadStepConfig
    onec_http_service: SourceWebApiWritebackOneCServiceConfig = Field(default_factory=SourceWebApiWritebackOneCServiceConfig)
    caller_response: SourceWebApiWritebackCallerResponseConfig = Field(default_factory=SourceWebApiWritebackCallerResponseConfig)


class SourceWebApiWritebackOneCPreviewResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    endpoint: dict[str, Any] = Field(default_factory=dict)
    incoming_request: Any = None
    odata_request: dict[str, Any] = Field(default_factory=dict)
    odata_result: dict[str, Any] | None = None
    site_payload: Any = None
    site_request: dict[str, Any] | None = None
    site_response: Any = None
    extraction: dict[str, Any] = Field(default_factory=dict)
    onec_writeback_payload: Any = None
    onec_writeback_request: dict[str, Any] | None = None
    onec_writeback_response: Any = None
    response_to_caller: Any = None
    human_steps: list[str] = Field(default_factory=list)
    advanced: dict[str, Any] = Field(default_factory=dict)


class SourceWebApiWritebackOneCCreateResponse(BaseModel):
    draft_id: UUID | None = None
    compile: CompileDraftResponse
    preview: SourceWebApiWritebackOneCPreviewResponse


class SourceWebApiWritebackOneCRunTestRequest(BaseModel):
    integration_flow_id: UUID
    dry_run: bool = True


class SourceWebApiWritebackOneCRunTestResponse(CompiledRunTestResponse):
    pass


class WmsFactToOneCODataLookupConfig(BaseModel):
    enabled: bool = True
    config: ODataStepConfig = Field(
        default_factory=lambda: ODataStepConfig(
            resource="Document_ЗаказКлиента",
            filter_mode="raw",
            filter_rule={"field": "Number", "operator": "eq", "value_type": "variable", "value": "request.body.order_number"},
            filter="Number eq '{{request.body.order_number}}'",
            select=["Ref_Key", "Number", "Date", "Posted"],
            top=1,
            paginate=False,
            save_as="order",
            required=True,
        )
    )
    order_ref_key_path: str = "request.body.order_ref_key"


class WmsFactToOneCServiceConfig(BaseModel):
    operation_id: UUID | None = None
    operation_code: str | None = None
    operation_name: str | None = None
    connector_id: UUID | None = None
    connector_name: str | None = None
    operation: str = "update_shipment_status"
    method: FinalActionMethod = "POST"
    base_url: str = "http://1c-server/erp/hs/omh"
    path: str = "/shipment-facts"
    url: str = ""
    headers: dict[str, Any] = Field(default_factory=lambda: {"Content-Type": "application/json"})
    body_source: str = "onec_payload"
    body_type: FinalActionBodyType = "json"
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    save_response_as: str = "onec_response"
    mock_response_json: Any = None


class WmsFactToOneCCallerResponseConfig(BaseModel):
    type: Literal["normalized", "raw_onec_response", "accepted_event"] = "normalized"
    status_code: int = Field(default=200, ge=100, le=599)
    body: Any = Field(
        default_factory=lambda: {
            "success": "{{onec_response.success}}",
            "wms_shipment_id": "{{request.body.wms_shipment_id}}",
            "order_number": "{{request.body.order_number}}",
            "onec_response": "{{onec_response}}",
        }
    )
    headers: dict[str, Any] = Field(default_factory=lambda: {"Content-Type": "application/json"})


class WmsFactToOneCPatternRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160)
    input_contract: InputContract
    odata_lookup: WmsFactToOneCODataLookupConfig = Field(default_factory=WmsFactToOneCODataLookupConfig)
    onec_payload: PayloadStepConfig
    onec_http_service: WmsFactToOneCServiceConfig = Field(default_factory=WmsFactToOneCServiceConfig)
    caller_response: WmsFactToOneCCallerResponseConfig = Field(default_factory=WmsFactToOneCCallerResponseConfig)


class WmsFactToOneCPreviewResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    endpoint: dict[str, Any] = Field(default_factory=dict)
    incoming_request: Any = None
    odata_request: dict[str, Any] = Field(default_factory=dict)
    odata_result: dict[str, Any] | None = None
    onec_payload: Any = None
    onec_request: dict[str, Any] | None = None
    onec_response: Any = None
    response_to_caller: Any = None
    human_steps: list[str] = Field(default_factory=list)
    advanced: dict[str, Any] = Field(default_factory=dict)


class WmsFactToOneCCreateResponse(BaseModel):
    draft_id: UUID | None = None
    compile: CompileDraftResponse
    preview: WmsFactToOneCPreviewResponse


class WmsFactToOneCRunTestRequest(BaseModel):
    integration_flow_id: UUID
    dry_run: bool = True


class WmsFactToOneCRunTestResponse(CompiledRunTestResponse):
    pass


class XmlRawBridgePolicyConfig(BaseModel):
    forward_unchanged: bool = True
    require_valid_xml: bool = True
    validate_xml: bool = True
    verify_hash: bool = True


class XmlRawBridgeTargetConfig(BaseModel):
    operation_id: UUID | None = None
    operation_code: str | None = None
    operation_name: str | None = None
    mode: Literal["onec_connector", "raw_url"] = "raw_url"
    connector_id: UUID | None = None
    connector_name: str | None = None
    method: FinalActionMethod = "POST"
    base_url: str = "http://1c-server/erp/hs/omh"
    path: str = "/receive-upd-xml"
    url: str = "http://1c-server/erp/hs/omh/receive-upd-xml"
    headers: dict[str, Any] = Field(default_factory=lambda: {"Content-Type": "application/xml; charset=utf-8"})
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    save_response_as: str = "target_response"
    training_mock_onec_xml_receiver: bool = False
    mock_response_json: Any = None
    mock_response_xml: str | None = None
    mock_response_text: str | None = None
    mock_status_code: int = Field(default=200, ge=100, le=599)


class XmlRawBridgeCallerResponseConfig(BaseModel):
    type: Literal["proxy_target_response", "fixed_success", "accepted_event", "custom_json", "custom_xml", "custom_raw"] = "proxy_target_response"
    status_code: int = Field(default=200, ge=100, le=599)
    body: Any = Field(default_factory=lambda: {"success": True, "xml_forwarded": True, "unchanged": "{{xml_hashes.unchanged}}", "target_response": "{{target_response}}"})
    headers: dict[str, Any] = Field(default_factory=lambda: {"Content-Type": "application/json"})


class XmlRawBridgePatternRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160)
    input_contract: InputContract
    raw_xml_policy: XmlRawBridgePolicyConfig = Field(default_factory=XmlRawBridgePolicyConfig)
    target: XmlRawBridgeTargetConfig = Field(default_factory=XmlRawBridgeTargetConfig)
    caller_response: XmlRawBridgeCallerResponseConfig = Field(default_factory=XmlRawBridgeCallerResponseConfig)


class XmlRawBridgePreviewResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    endpoint: dict[str, Any] = Field(default_factory=dict)
    incoming_xml: str = ""
    xml_paths: list[dict[str, Any]] = Field(default_factory=list)
    raw_xml_policy: dict[str, Any] = Field(default_factory=dict)
    target_request: dict[str, Any] | None = None
    target_response: Any = None
    hash_check: dict[str, Any] = Field(default_factory=dict)
    response_to_caller: Any = None
    human_steps: list[str] = Field(default_factory=list)
    advanced: dict[str, Any] = Field(default_factory=dict)


class XmlRawBridgeCreateResponse(BaseModel):
    draft_id: UUID | None = None
    compile: CompileDraftResponse
    preview: XmlRawBridgePreviewResponse


class XmlRawBridgeRunTestRequest(BaseModel):
    integration_flow_id: UUID
    dry_run: bool = True


class XmlRawBridgeRunTestResponse(CompiledRunTestResponse):
    pass


class XmlODataXmlExtractField(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    path: str = Field(min_length=1, max_length=500)
    required: bool = True
    mode: Literal["first", "all"] = "first"
    example: Any = None


class XmlODataXmlExtractConfig(BaseModel):
    fields: list[XmlODataXmlExtractField] = Field(
        default_factory=lambda: [
            XmlODataXmlExtractField(name="operation", path="/Request/Operation", required=True, example="lookup_order"),
            XmlODataXmlExtractField(name="order_number", path="/Request/Number", required=True, example="260666/6938"),
            XmlODataXmlExtractField(name="format", path="/Request/Format", required=False, example="xml"),
        ]
    )


class XmlODataXmlResponseConfig(BaseModel):
    body_type: PayloadBodyType = "xml"
    status_code: int = Field(default=200, ge=100, le=599)
    template: Any = Field(
        default="""<Response>
  <Success>true</Success>
  <Order>
    <UUID>{{order.Ref_Key}}</UUID>
    <Number>{{order.Number}}</Number>
    <Date>{{order.Date}}</Date>
    <Posted>{{order.Posted}}</Posted>
  </Order>
</Response>"""
    )
    headers: dict[str, Any] = Field(default_factory=lambda: {"Content-Type": "application/xml; charset=utf-8"})


class XmlODataXmlResponsePatternRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160)
    input_contract: InputContract
    xml_extract: XmlODataXmlExtractConfig = Field(default_factory=XmlODataXmlExtractConfig)
    odata_step: ODataStepConfig = Field(default_factory=ODataStepConfig)
    response: XmlODataXmlResponseConfig = Field(default_factory=XmlODataXmlResponseConfig)


class XmlODataXmlResponsePreviewResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    endpoint: dict[str, Any] = Field(default_factory=dict)
    incoming_xml: str = ""
    xml_paths: list[dict[str, Any]] = Field(default_factory=list)
    extracted_variables: dict[str, Any] = Field(default_factory=dict)
    odata_request: dict[str, Any] = Field(default_factory=dict)
    odata_result: dict[str, Any] | list[dict[str, Any]] | None = None
    response_to_caller: Any = None
    human_steps: list[str] = Field(default_factory=list)
    advanced: dict[str, Any] = Field(default_factory=dict)


class XmlODataXmlResponseCreateResponse(BaseModel):
    draft_id: UUID | None = None
    compile: CompileDraftResponse
    preview: XmlODataXmlResponsePreviewResponse


class XmlODataXmlResponseRunTestRequest(BaseModel):
    integration_flow_id: UUID
    dry_run: bool = True


class XmlODataXmlResponseRunTestResponse(CompiledRunTestResponse):
    pass


class RequestPrintPrinterSelectionConfig(BaseModel):
    mode: Literal["from_request", "fixed", "rule_based"] = "from_request"
    path: str = "request.body.printer"
    fixed_printer_name: str = "LINE-1-ZEBRA"


class RequestPrintLabelsConfig(BaseModel):
    path: str = "request.body.labels"
    item_as: str = "label"
    required_fields: list[str] = Field(default_factory=lambda: ["code"])
    optional_fields: list[str] = Field(default_factory=lambda: ["sku", "title", "qty", "sequence_no"])


class RequestPrintZplConfig(BaseModel):
    template: str = Field(
        default="""^XA
^CI28
^FO30,30^A0N,30,30^FD{{label.title}}^FS
^FO30,70^A0N,24,24^FDSKU: {{label.sku}}^FS
^FO30,110^BXN,5,200^FD{{label.code}}^FS
^FO30,300^A0N,24,24^FD#{{label.sequence_no}} / {{request.body.job_key}}^FS
^XZ"""
    )


class RequestPrintPrintModeConfig(BaseModel):
    mode: Literal["dry_run", "test_one_label", "print_all"] = "dry_run"


class RequestPrintCallerResponseConfig(BaseModel):
    type: Literal["normalized_print_status", "raw_printer_response", "accepted_event"] = "normalized_print_status"
    status_code: int = Field(default=200, ge=100, le=599)
    body: Any = Field(
        default_factory=lambda: {
            "success": True,
            "print_job_id": "{{print_job.id}}",
            "labels_count": "{{labels.length}}",
            "printer": "{{selected_printer.name}}",
            "status": "{{print_job.status}}",
        }
    )
    headers: dict[str, Any] = Field(default_factory=lambda: {"Content-Type": "application/json"})


class RequestPrintPatternRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160)
    input_contract: InputContract
    printer_selection: RequestPrintPrinterSelectionConfig = Field(default_factory=RequestPrintPrinterSelectionConfig)
    labels: RequestPrintLabelsConfig = Field(default_factory=RequestPrintLabelsConfig)
    zpl: RequestPrintZplConfig = Field(default_factory=RequestPrintZplConfig)
    print_mode: RequestPrintPrintModeConfig = Field(default_factory=RequestPrintPrintModeConfig)
    response: RequestPrintCallerResponseConfig = Field(default_factory=RequestPrintCallerResponseConfig)


class RequestPrintPreviewResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    endpoint: dict[str, Any] = Field(default_factory=dict)
    incoming_request: Any = None
    selected_printer: dict[str, Any] | None = None
    labels_count: int = 0
    rendered_zpl_first_label: str = ""
    rendered_zpl_all_labels: str = ""
    print_action: str = "dry_run"
    response_to_caller: Any = None
    human_steps: list[str] = Field(default_factory=list)
    advanced: dict[str, Any] = Field(default_factory=dict)


class RequestPrintCreateResponse(BaseModel):
    draft_id: UUID | None = None
    compile: CompileDraftResponse
    preview: RequestPrintPreviewResponse


class RequestPrintRunTestRequest(BaseModel):
    integration_flow_id: UUID
    dry_run: bool = True


class RequestPrintRunTestResponse(CompiledRunTestResponse):
    pass


class RequestPrintTestPrintRequest(RequestPrintPatternRequest):
    dry_run: bool = True
    limit: int = Field(default=1, ge=1, le=1000)


class RequestPrintTestPrintResponse(BaseModel):
    preview: RequestPrintPreviewResponse
    print_result: dict[str, Any] = Field(default_factory=dict)
