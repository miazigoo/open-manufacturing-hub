from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MarkingCodePoolActionOverrides(BaseModel):
    local_outbox: bool | None = None
    laser_file: bool | None = None
    external_forward: bool | None = None


class OneCMarkingCodePoolExportRequest(BaseModel):
    source_system: str = Field(default="1C ERP", min_length=1, max_length=255)
    source_document_id: str | None = Field(default=None, max_length=255)
    source_document_name: str | None = Field(default=None, max_length=255)
    order_number: str = Field(min_length=1, max_length=255)
    file_name: str | None = Field(default=None, max_length=255)
    codes: list[str] | None = Field(default=None, min_length=1)
    full_codes_base64: list[str] | None = Field(default=None, min_length=1)
    gs_marker: str = Field(default="{GS}", min_length=1, max_length=20)
    allow_overwrite: bool | None = None
    actions_override: MarkingCodePoolActionOverrides | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_one_code_source(self):
        if bool(self.codes) == bool(self.full_codes_base64):
            raise ValueError("Pass exactly one of codes or full_codes_base64")
        return self


class MarkingCodePoolOverview(BaseModel):
    settings: MarkingCodePoolSettingsRead
    latest_export: MarkingCodePoolExportRead | None = None
    recent_errors: list[MarkingCodePoolExportRead] = []
    total_exports: int = 0


class MarkingCodePoolExportRead(BaseModel):
    id: UUID
    source_system: str
    source_document_id: str | None
    source_document_name: str | None
    order_number: str
    file_name: str
    file_path: str
    total_codes: int
    content_sha256: str
    status: str
    error_message: str | None
    metadata_json: dict[str, Any]
    forwarded_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarkingCodePoolExportResponse(BaseModel):
    export: MarkingCodePoolExportRead
    message: str
    success: bool = True
    status: str = "saved"
    warnings: list[str] = Field(default_factory=list)
    actions: dict[str, Any] = Field(default_factory=dict)
    segments: list[dict[str, Any]] = Field(default_factory=list)
    external_forward: dict[str, Any] | None = None
    dnp_forward: dict[str, Any] | None = None


class MarkingCodePoolLocalOutboxSettings(BaseModel):
    enabled: bool = True
    required: bool = True
    export_dir: str
    file_name_template: str = "KM_{{order_number_safe}}___{{total_codes_formatted}}_pcs.txt"
    allow_overwrite_default: bool = True
    note: str = "Локальное сохранение обязательно и используется как архив."


class MarkingCodePoolLaserSettings(BaseModel):
    enabled: bool = False
    smb_unc: str = ""
    username: str = "guest"
    password_set: bool = False


class MarkingCodePoolForwardSettings(BaseModel):
    enabled: bool = False
    service_name: str = "DnP"
    url: str = ""
    method: str = "POST"
    header_name: str = "X-OMH-Token"
    token_set: bool = False
    timeout_seconds: float = 600.0


class MarkingCodePoolResponseSettings(BaseModel):
    success_mode: str = "partial_success_allowed"


class MarkingCodePoolSettingsRead(BaseModel):
    local_outbox: MarkingCodePoolLocalOutboxSettings
    laser: MarkingCodePoolLaserSettings
    forward: MarkingCodePoolForwardSettings
    response: MarkingCodePoolResponseSettings
    source: str


class MarkingCodePoolSettingsPatch(BaseModel):
    local_outbox_enabled: bool | None = None
    export_dir: str | None = Field(default=None, min_length=1)
    file_name_template: str | None = Field(default=None, min_length=1, max_length=255)
    allow_overwrite_default: bool | None = None
    laser_enabled: bool | None = None
    laser_smb_unc: str | None = None
    laser_smb_username: str | None = None
    laser_smb_password: str | None = None
    forward_enabled: bool | None = None
    forward_service_name: str | None = None
    forward_url: str | None = None
    forward_method: str | None = None
    forward_header_name: str | None = None
    forward_token: str | None = None
    forward_timeout_seconds: float | None = Field(default=None, gt=0)
    response_success_mode: str | None = None


class MarkingCodePoolPreviewResponse(BaseModel):
    success: bool
    file_name: str
    total_codes: int
    content_sha256: str
    would_save_to: str
    would_laser_copy: dict[str, Any]
    would_forward: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)
    segments: list[dict[str, Any]] = Field(default_factory=list)


class MarkingCodePoolSettingsTestRequest(BaseModel):
    dry_run: bool = True


class MarkingCodePoolForwardTestRequest(BaseModel):
    send_test_request: bool = False


class MarkingCodePoolSettingsTestResponse(BaseModel):
    success: bool
    status: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class MarkingCodePoolActionRetryResponse(BaseModel):
    success: bool
    status: str
    message: str
    error_code: str | None = None
    action: dict[str, Any] = Field(default_factory=dict)


ROUTING_TARGET_TYPES = {"laser_file", "local_outbox", "http_forward"}


class RoutingRuleTarget(BaseModel):
    type: str
    file_name_template: str | None = Field(default=None, max_length=255)
    name: str | None = Field(default=None, max_length=255)
    url: str | None = Field(default=None, max_length=2000)
    method: str = Field(default="POST", max_length=10)
    header_name: str | None = Field(default=None, max_length=255)
    token: str | None = Field(default=None, max_length=2000)
    timeout_seconds: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_target(self):
        if self.type not in ROUTING_TARGET_TYPES:
            raise ValueError(f"Unsupported routing target type: {self.type}")
        if self.type == "http_forward":
            if not self.url:
                raise ValueError("http_forward target requires url")
            if self.method.upper() != "POST":
                raise ValueError("http_forward target supports only POST")
        return self


class MarkingCodePoolRoutingRuleRead(BaseModel):
    id: UUID
    name: str
    enabled: bool
    priority: int
    match_json: dict[str, Any]
    targets_json: list[dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarkingCodePoolRoutingRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    enabled: bool = True
    priority: int = 100
    match_json: dict[str, Any] = Field(default_factory=dict)
    targets_json: list[RoutingRuleTarget] = Field(default_factory=list)


class MarkingCodePoolRoutingRulePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    enabled: bool | None = None
    priority: int | None = None
    match_json: dict[str, Any] | None = None
    targets_json: list[RoutingRuleTarget] | None = None


class RoutingRuleTestRequest(BaseModel):
    codes: list[str] | None = Field(default=None, min_length=1)
    full_codes_base64: list[str] | None = Field(default=None, min_length=1)
    gs_marker: str = Field(default="{GS}", min_length=1, max_length=20)
    order_number: str = Field(default="", max_length=255)
    source_document_id: str | None = Field(default=None, max_length=255)
    source_system: str = Field(default="1C ERP", max_length=255)

    @model_validator(mode="after")
    def require_one_code_source(self):
        if bool(self.codes) == bool(self.full_codes_base64):
            raise ValueError("Pass exactly one of codes or full_codes_base64")
        return self


class RoutingRuleTestCodeResult(BaseModel):
    code_preview: str
    gtin: str
    serial: str
    segment: str
    rule_id: UUID | None
    rule_name: str | None
    targets: list[dict[str, Any]] = Field(default_factory=list)


class RoutingRuleTestResponse(BaseModel):
    total_codes: int
    matched_codes: int
    default_codes: int
    results: list[RoutingRuleTestCodeResult]
