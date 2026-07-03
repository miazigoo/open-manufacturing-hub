from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import PrintJobStatus, PrintLineStatus


class PrintPrinterCreate(BaseModel):
    name: str
    connector_id: UUID
    dpi: int = Field(gt=0, le=2400)
    enabled: bool = True
    description: str | None = None
    settings_json: dict[str, Any] = Field(default_factory=dict)


class PrintPrinterPatch(BaseModel):
    name: str | None = None
    connector_id: UUID | None = None
    dpi: int | None = Field(default=None, gt=0, le=2400)
    enabled: bool | None = None
    description: str | None = None
    settings_json: dict[str, Any] | None = None


class PrintPrinterRead(BaseModel):
    id: UUID
    name: str
    connector_id: UUID
    dpi: int
    enabled: bool
    description: str | None
    settings_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrintJobLineCreate(BaseModel):
    sequence_no: int = Field(gt=0)
    code: str = Field(min_length=1)
    zpl: str = Field(min_length=1)


class PrintJobCreate(BaseModel):
    job_key: str = Field(min_length=1, max_length=255)
    printer_id: UUID
    source_system: str = Field(min_length=1, max_length=255)
    source_document_id: str | None = None
    source_document_name: str | None = None
    label_settings_json: dict[str, Any] = Field(default_factory=dict)
    lines: list[PrintJobLineCreate] = Field(min_length=1)


class PrintJobRead(BaseModel):
    id: UUID
    job_key: str
    printer_id: UUID
    source_system: str
    source_document_id: str | None
    source_document_name: str | None
    status: PrintJobStatus
    label_settings_json: dict[str, Any]
    total_lines: int
    sent_lines: int
    printed_lines: int
    error_lines: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrintJobLineRead(BaseModel):
    id: UUID
    job_id: UUID
    sequence_no: int
    code_visible: str
    code_sha256: str
    zpl_sha256: str
    status: PrintLineStatus
    attempts: int
    last_error: str | None
    sent_at: datetime | None
    printed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrintJobLogRead(BaseModel):
    id: UUID
    job_id: UUID
    line_id: UUID | None
    sequence_no: int | None
    action: str
    status: str
    message: str | None
    details_json: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PrintBatchRequest(BaseModel):
    limit: int = Field(default=100, gt=0, le=1000)
    start_sequence_no: int | None = Field(default=None, gt=0)
    dry_run: bool = True
    include_returned: bool = True


class PrintBatchLineResult(BaseModel):
    line_id: UUID
    sequence_no: int
    status: PrintLineStatus
    success: bool
    error_code: str | None = None
    error_message: str | None = None


class PrintBatchResponse(BaseModel):
    job: PrintJobRead
    processed: int
    sent: int
    failed: int
    dry_run: bool
    results: list[PrintBatchLineResult]


class ConfirmPrintedRequest(BaseModel):
    through_sequence_no: int | None = Field(default=None, gt=0)
    line_ids: list[UUID] | None = None


class ReturnToPrintRequest(BaseModel):
    from_sequence_no: int = Field(gt=0)
    reason: str | None = None
