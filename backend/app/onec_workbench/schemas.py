from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import IntegrationMessageDirection, IntegrationMessageStatus


class XmlInboundJsonRequest(BaseModel):
    source_system: str = Field(min_length=1)
    target_system: str | None = None
    message_type: str = Field(default="XML_FILE", min_length=1)
    correlation_id: str | None = None
    external_id: str | None = None
    document_type: str | None = None
    document_number: str | None = None
    xml: str = Field(min_length=1)


class XmlInboundResponse(BaseModel):
    message_id: UUID
    event_id: UUID
    status: IntegrationMessageStatus
    timeline_url: str


class IntegrationMessageRead(BaseModel):
    id: UUID
    direction: IntegrationMessageDirection
    source_system: str
    target_system: str | None
    message_type: str
    document_type: str | None
    document_number: str | None
    document_date: datetime | None
    correlation_id: str | None
    external_id: str | None
    status: IntegrationMessageStatus
    route_key: str | None
    content_type: str
    payload_text: str | None
    payload_json: dict[str, Any] | None
    payload_sha256: str
    payload_size_bytes: int
    event_id: UUID | None
    last_error: str | None
    expires_at: datetime | None
    pinned: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ODataLookupTestRequest(BaseModel):
    connector_name: str
    resource: str
    filter_template: str
    input: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    extract: dict[str, str] = Field(default_factory=dict)
    required: bool = True


class ODataLookupTestResponse(BaseModel):
    request: dict[str, Any]
    response: dict[str, Any]
    extracted: dict[str, Any]


class WorkbenchInstallResponse(BaseModel):
    workflow_id: UUID
    workflow_name: str
    installed: bool
