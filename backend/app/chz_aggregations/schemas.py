from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class ChzAggregationCodeRow(BaseModel):
    code: str | None = None
    full_code: str | None = None
    full_code_base64: str | None = None
    aggregate_code: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def require_one_code_source(self):
        if bool(self.code or self.full_code) == bool(self.full_code_base64):
            raise ValueError("Pass exactly one of code/full_code or full_code_base64")
        return self


class ChzAggregationGroupInput(BaseModel):
    aggregate_code: str = Field(min_length=1, max_length=255)
    codes: list[str] | None = Field(default=None, min_length=1)
    full_codes_base64: list[str] | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_one_code_source(self):
        if bool(self.codes) == bool(self.full_codes_base64):
            raise ValueError("Pass exactly one of codes or full_codes_base64")
        return self


class ChzAggregationRegistrationRequest(BaseModel):
    source_system: str = Field(default="External aggregation service", min_length=1, max_length=255)
    source_document_id: str | None = Field(default=None, max_length=255)
    source_file_name: str | None = Field(default=None, max_length=255)
    order_number: str | None = Field(default=None, max_length=255)
    order_number_1c: str | None = Field(default=None, max_length=255)
    order_number_external: str | None = Field(default=None, max_length=255)
    rows: list[ChzAggregationCodeRow] | None = Field(default=None, min_length=1)
    aggregates: list[ChzAggregationGroupInput] | None = Field(default=None, min_length=1)
    metadata_json: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_one_payload_shape(self):
        if bool(self.rows) == bool(self.aggregates):
            raise ValueError("Pass exactly one of rows or aggregates")
        return self


class ChzAggregationPreviewResponse(BaseModel):
    success: bool
    status: str
    order_number_1c: str
    order_number_external: str | None
    total_codes: int
    total_aggregates: int
    content_sha256: str
    duplicate_codes: int
    warnings: list[str] = Field(default_factory=list)
    sample: dict[str, Any] = Field(default_factory=dict)


class ChzAggregationRegistrationRead(BaseModel):
    id: UUID
    source_system: str
    source_document_id: str | None
    source_file_name: str | None
    order_number_1c: str
    order_number_external: str | None
    total_codes: int
    total_aggregates: int
    content_sha256: str
    status: str
    error_message: str | None
    metadata_json: dict[str, Any]
    forwarded_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChzAggregationRegistrationResponse(BaseModel):
    success: bool
    status: str
    message: str
    registration: ChzAggregationRegistrationRead
    onec_response: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)


class ChzAggregationSettingsRead(BaseModel):
    onec_enabled: bool
    onec_url: str
    method: str = "POST"
    header_name: str = "X-OMH-Token"
    token_set: bool = False
    timeout_seconds: float
    source: str


class ChzAggregationSettingsPatch(BaseModel):
    onec_enabled: bool | None = None
    onec_url: str | None = None
    onec_token: str | None = None
    onec_header_name: str | None = None
    onec_timeout_seconds: float | None = Field(default=None, gt=0, allow_inf_nan=False)

    @field_validator("onec_url")
    @classmethod
    def validate_http_url(cls, value: str | None) -> str | None:
        if value and value.strip():
            parsed = HttpUrl(value.strip())
            if parsed.username is not None or parsed.password is not None:
                raise ValueError("Для логина и пароля используйте поля авторизации.")
        return value

    @field_validator("onec_header_name")
    @classmethod
    def validate_header_name(cls, value: str | None) -> str | None:
        if value and value.strip() and not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", value.strip()):
            raise ValueError("Некорректное имя HTTP-заголовка.")
        return value

    @field_validator("onec_token")
    @classmethod
    def validate_token(cls, value: str | None) -> str | None:
        if value and not re.fullmatch(r"[ -~]+", value):
            raise ValueError("Значение HTTP-заголовка должно состоять из печатных ASCII-символов.")
        return value


class ChzDnpPullRequest(BaseModel):
    order_number_1c: str = Field(min_length=1, max_length=255)
    date_from: date | None = None
    date_to: date | None = None
    only_new: bool = True


class ChzDnpPullRow(BaseModel):
    full_code_base64: str
    sscc: str | None = None


class ChzDnpPullResponse(BaseModel):
    ok: bool
    order_number_1c: str
    order_name_dnp: str | None = None
    codes_count: int
    boxes_count: int
    tsv_text_base64: str
    rows: list[ChzDnpPullRow] = Field(default_factory=list)
    event_id: UUID | None = None
    timeline_url: str | None = None
