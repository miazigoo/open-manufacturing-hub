from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TestConsoleSendRequest(BaseModel):
    endpoint_id: UUID | None = None
    slug: str | None = None
    input_mode: str = "json"
    headers_json: dict[str, str] = Field(default_factory=dict)
    body_text: str | None = None
    body_json: dict[str, Any] | None = None
    dry_run: bool = False


class TestConsoleSendResponse(BaseModel):
    success: bool
    response: dict[str, Any]
    event_id: UUID | None = None
    message_id: UUID | None = None
    timeline_url: str | None = None
    external_error: dict[str, Any] | None = None
    dry_run: bool = False


class SavedTestCaseCreate(BaseModel):
    name: str
    description: str | None = None
    endpoint_id: UUID | None = None
    method: str = "POST"
    headers_json: dict[str, Any] | None = None
    body_text: str | None = None
    body_json: dict[str, Any] | None = None
    input_mode: str = "json"
    expected_status: str | None = None


class SavedTestCasePatch(BaseModel):
    name: str | None = None
    description: str | None = None
    endpoint_id: UUID | None = None
    method: str | None = None
    headers_json: dict[str, Any] | None = None
    body_text: str | None = None
    body_json: dict[str, Any] | None = None
    input_mode: str | None = None
    expected_status: str | None = None


class SavedTestCaseRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    endpoint_id: UUID | None
    method: str
    headers_json: dict[str, Any] | None
    body_text: str | None
    body_json: dict[str, Any] | None
    input_mode: str
    expected_status: str | None
    last_run_event_id: UUID | None
    last_run_status: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
