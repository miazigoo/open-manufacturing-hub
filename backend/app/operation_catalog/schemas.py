from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

OperationKind = Literal["rest_api_operation", "onec_http_operation", "printer_operation", "file_operation", "training_operation"]
OperationBodyType = Literal["json", "xml", "raw_text", "form", "none"]
OperationMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
SuccessConditionType = Literal["http_status_2xx", "http_status_equals", "json_path_equals", "json_path_exists", "response_contains_text", "always_success"]


class SuccessCondition(BaseModel):
    type: SuccessConditionType
    status: int | None = Field(default=None, ge=100, le=599)
    path: str | None = None
    value: Any = None
    text: str | None = None


class SuccessConditionGroup(BaseModel):
    mode: Literal["all", "any"] = "all"
    conditions: list[SuccessCondition] = Field(default_factory=lambda: [SuccessCondition(type="http_status_2xx")])


class ResponseExtractor(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    path: str = Field(min_length=1, max_length=240)
    required: bool = False


class OperationProfileBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=180)
    kind: OperationKind
    connection_profile_id: UUID | None = None
    request_contract_id: UUID | None = None
    response_contract_id: UUID | None = None
    description: str | None = None
    enabled: bool = True
    method: OperationMethod | None = None
    path: str | None = None
    full_url: str | None = None
    headers_json: dict[str, Any] | None = None
    body_type: OperationBodyType | None = None
    request_template_json: dict[str, Any] | list[Any] | None = None
    request_template_text: str | None = None
    response_body_type: OperationBodyType | None = None
    success_condition_json: dict[str, Any] | None = None
    response_extractors_json: list[dict[str, Any]] | None = None
    sample_request_json: dict[str, Any] | list[Any] | None = None
    sample_response_json: dict[str, Any] | list[Any] | str | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    tags_json: list[str] | None = None
    package_id: str | None = None


class OperationProfileCreate(OperationProfileBase):
    pass


class OperationProfilePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=180)
    kind: OperationKind | None = None
    connection_profile_id: UUID | None = None
    request_contract_id: UUID | None = None
    response_contract_id: UUID | None = None
    description: str | None = None
    enabled: bool | None = None
    method: OperationMethod | None = None
    path: str | None = None
    full_url: str | None = None
    headers_json: dict[str, Any] | None = None
    body_type: OperationBodyType | None = None
    request_template_json: dict[str, Any] | list[Any] | None = None
    request_template_text: str | None = None
    response_body_type: OperationBodyType | None = None
    success_condition_json: dict[str, Any] | None = None
    response_extractors_json: list[dict[str, Any]] | None = None
    sample_request_json: dict[str, Any] | list[Any] | None = None
    sample_response_json: dict[str, Any] | list[Any] | str | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=300)
    tags_json: list[str] | None = None
    package_id: str | None = None


class OperationProfileRead(OperationProfileBase):
    id: UUID
    connection_name: str | None = None
    connection_kind: str | None = None
    final_url: str | None = None
    used_by: list[str] = Field(default_factory=list)
    last_test_at: datetime | None = None
    last_test_success: bool | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OperationProfileOption(BaseModel):
    id: UUID
    label: str
    name: str
    code: str
    kind: OperationKind
    connection_profile_id: UUID | None = None
    request_contract_id: UUID | None = None
    response_contract_id: UUID | None = None
    connection_name: str | None = None
    connection_kind: str | None = None
    method: str | None = None
    path: str | None = None
    full_url: str | None = None
    final_url: str | None = None
    headers_json: dict[str, Any] | None = None
    body_type: str | None = None
    response_body_type: str | None = None
    timeout_seconds: int | None = None
    tags: list[str] = Field(default_factory=list)
    used_by: list[str] = Field(default_factory=list)


class OperationCatalogOptions(BaseModel):
    operations: list[OperationProfileOption]
    by_kind: dict[str, list[OperationProfileOption]]


class OperationTestRequest(BaseModel):
    dry_run: bool = True
    confirm_real_request: bool = False
    mock_response: bool = True
    request_body: Any = None
    response_body: Any = None
    http_status: int = Field(default=200, ge=100, le=599)


class OperationSuccessConditionResult(BaseModel):
    success: bool
    mode: str
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class OperationTestResponse(BaseModel):
    success: bool
    status: str
    message: str
    operation_id: UUID
    dry_run: bool
    final_url: str | None = None
    method: str | None = None
    request: dict[str, Any] = Field(default_factory=dict)
    response: dict[str, Any] = Field(default_factory=dict)
    http_status: int | None = None
    response_body: Any = None
    success_condition_result: OperationSuccessConditionResult | None = None
    extracted: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class InstallPresetsResponse(BaseModel):
    installed: list[OperationProfileRead]
    skipped: list[str] = Field(default_factory=list)
