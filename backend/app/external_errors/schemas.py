from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ExternalErrorSummary(BaseModel):
    id: UUID
    event_id: UUID | None = None
    run_id: UUID | None = None
    step_id: UUID | None = None
    incident_id: UUID | None = None
    source_system: str | None = None
    target_system: str | None = None
    connector_type: str | None = None
    connector_name: str | None = None
    operation: str | None = None
    endpoint_url: str | None = None
    http_method: str | None = None
    http_status: int | None = None
    normalized_code: str
    normalized_message: str
    human_title: str | None = None
    human_summary: str | None = None
    developer_message: str | None = None
    hint: str | None = None
    external_error_code: str | None = None
    external_error_message: str | None = None
    external_error_type: str | None = None
    response_content_type: str | None = None
    response_body_preview: str | None = None
    response_body_sha256: str | None = None
    response_size_bytes: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExternalErrorRead(ExternalErrorSummary):
    response_body_text: str | None = None
    response_body_json: Any | None = None
    response_body_xml: str | None = None
    request_artifact_id: UUID | None = None
    response_artifact_id: UUID | None = None
    error_artifact_id: UUID | None = None
