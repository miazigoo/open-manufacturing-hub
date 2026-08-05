from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    onec_url: str
    method: str = "POST"
    header_name: str = "X-OMH-Token"
    token_set: bool = False
    timeout_seconds: float
    source: str


class ChzAggregationSettingsPatch(BaseModel):
    onec_url: str | None = None
    onec_token: str | None = None
    onec_header_name: str | None = None
    onec_timeout_seconds: float | None = Field(default=None, gt=0)


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
