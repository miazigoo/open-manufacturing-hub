from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LocalizedText(BaseModel):
    ru: str
    en: str
    zh: str


class DocsExampleRead(BaseModel):
    id: str
    title: LocalizedText
    description: LocalizedText
    endpoint_slug: str
    method: str = "POST"
    input_mode: str = "json"
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] | None = None
    body_text: str | None = None
    expected: dict[str, Any] = Field(default_factory=dict)
    runnable: bool = False
    requires_setup: bool = True


class DocsExampleRunResponse(BaseModel):
    success: bool
    example_id: str
    runnable: bool
    requires_setup: bool
    dry_run: bool = False
    response: dict[str, Any]
    event_id: str | None = None
    message_id: str | None = None
    timeline_url: str | None = None
    external_error: dict[str, Any] | None = None
