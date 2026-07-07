from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

InputMode = Literal["json", "xml", "raw_text"]
ResponseMode = Literal["sync_response", "accepted_event", "proxy_response"]
BodyType = Literal["json", "xml", "raw_text"]
AuthMode = Literal["none", "static_token"]


class ODataMasterOperationKey(BaseModel):
    field: str | None = "operation"
    value: str | None = None
    custom_field: str | None = None


class ODataMasterSource(BaseModel):
    system: str = "external_api"
    input_mode: InputMode = "json"
    sample: Any = Field(default_factory=dict)
    operation_key: ODataMasterOperationKey = Field(default_factory=ODataMasterOperationKey)
    endpoint_slug: str | None = None
    auth_mode: AuthMode = "none"
    auth_config_json: dict[str, Any] = Field(default_factory=dict)


class ODataQueryStep(BaseModel):
    type: Literal["odata_query"] = "odata_query"
    connection: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    filter: str | None = None
    select: list[str] = Field(default_factory=list)
    top: int | None = Field(default=100, ge=1)
    orderby: str | None = None
    paginate: bool = False
    required: bool = True
    save_as: str = Field(min_length=1)
    name: str | None = None

    @field_validator("select", mode="before")
    @classmethod
    def normalize_select(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


class ODataObjectStep(BaseModel):
    type: Literal["odata_object_query"] = "odata_object_query"
    connection: str = Field(min_length=1)
    base_resource: str = Field(min_length=1)
    object_key: str = Field(min_length=1)
    tabular_part: str | None = None
    filter: str | None = None
    select: list[str] = Field(default_factory=list)
    top: int | None = Field(default=100, ge=1)
    orderby: str | None = None
    paginate: bool = False
    required: bool = True
    save_as: str = Field(min_length=1)
    name: str | None = None

    @field_validator("select", mode="before")
    @classmethod
    def normalize_select(cls, value: Any) -> list[str]:
        return ODataQueryStep.normalize_select(value)


class ODataForeachStep(BaseModel):
    type: Literal["foreach_odata"] = "foreach_odata"
    items: str = Field(min_length=1)
    item_as: str = "item"
    connection: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    filter: str | None = None
    select: list[str] = Field(default_factory=list)
    top: int | None = Field(default=100, ge=1)
    orderby: str | None = None
    paginate: bool = False
    required: bool = False
    merge: Literal["flatten", "grouped", "first"] = "flatten"
    save_as: str = Field(min_length=1)
    name: str | None = None

    @field_validator("select", mode="before")
    @classmethod
    def normalize_select(cls, value: Any) -> list[str]:
        return ODataQueryStep.normalize_select(value)


WizardStep = ODataQueryStep | ODataObjectStep | ODataForeachStep


class ODataResponseSpec(BaseModel):
    mode: ResponseMode = "sync_response"
    body_type: BodyType = "json"
    body: Any = Field(default_factory=lambda: {"ok": True})
    return_target_response: bool = False


class ODataFinalAction(BaseModel):
    type: Literal["return_response", "send_endpoint", "send_onec_http_service", "async_accepted"] = "return_response"
    method: str = "POST"
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    body_type: BodyType = "json"
    body: Any = Field(default_factory=dict)
    response_to_caller: ODataResponseSpec = Field(default_factory=ODataResponseSpec)

    @field_validator("method")
    @classmethod
    def normalize_method(cls, value: str) -> str:
        return (value or "POST").upper()


class ODataWizardSpec(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9][a-z0-9_-]*[a-z0-9]$|^[a-z0-9]$")
    description: str | None = None
    source: ODataMasterSource = Field(default_factory=ODataMasterSource)
    steps: list[WizardStep] = Field(default_factory=list)
    final_action: ODataFinalAction = Field(default_factory=ODataFinalAction)

    @model_validator(mode="after")
    def ensure_steps(self) -> "ODataWizardSpec":
        if not self.steps:
            raise ValueError("Добавьте хотя бы один OData-шаг.")
        return self


class ODataMasterPreviewRequest(BaseModel):
    spec: ODataWizardSpec
    run_real_queries: bool = False


class ODataMasterSaveRequest(BaseModel):
    spec: ODataWizardSpec
    enabled: bool = True


class ODataMasterRunTestRequest(BaseModel):
    spec: ODataWizardSpec | None = None
    flow_id: UUID | None = None
    run_real_queries: bool = True
    dry_run: bool = False
    payload_json: dict[str, Any] | None = None
    payload_text: str | None = None
    headers_json: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def ensure_target(self) -> "ODataMasterRunTestRequest":
        if self.spec is None and self.flow_id is None:
            raise ValueError("Передайте spec для preview-run или flow_id для теста сохраненной интеграции.")
        return self


class ODataMasterExample(BaseModel):
    key: str
    title: str
    description: str
    spec: ODataWizardSpec


class ODataMasterCompileResponse(BaseModel):
    builder_json: dict[str, Any]
    flow_payload: dict[str, Any]
    validation: dict[str, Any]


class ODataMasterPreviewResponse(ODataMasterCompileResponse):
    preview: dict[str, Any]


class ODataMasterSaveResponse(BaseModel):
    integration_flow: dict[str, Any]
    endpoint_url: str
    next_steps: list[str]


class ODataMasterArtifactChecklistItem(BaseModel):
    step_id: str
    step_name: str
    step_type: str
    artifacts: list[str]
    notes: list[str] = Field(default_factory=list)


class ODataMasterRunDiagnostics(BaseModel):
    status: str | None = None
    event_id: UUID | None = None
    timeline_url: str | None = None
    artifact_checklist: list[ODataMasterArtifactChecklistItem] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class ODataMasterRunTestResponse(BaseModel):
    mode: Literal["preview", "saved_flow"]
    result: dict[str, Any]
    diagnostics: ODataMasterRunDiagnostics | None = None
