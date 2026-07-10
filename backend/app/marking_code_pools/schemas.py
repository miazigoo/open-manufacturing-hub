from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OneCMarkingCodePoolExportRequest(BaseModel):
    source_system: str = Field(default="1C ERP", min_length=1, max_length=255)
    source_document_id: str | None = Field(default=None, max_length=255)
    source_document_name: str | None = Field(default=None, max_length=255)
    order_number: str = Field(min_length=1, max_length=255)
    file_name: str | None = Field(default=None, max_length=255)
    codes: list[str] = Field(min_length=1)
    gs_marker: str = Field(default="{GS}", min_length=1, max_length=20)
    allow_overwrite: bool = True
    metadata_json: dict[str, Any] = Field(default_factory=dict)


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
