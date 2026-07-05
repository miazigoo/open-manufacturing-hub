from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OnboardingStateRead(BaseModel):
    id: UUID | None = None
    key: str
    title: str
    description: str
    route: str | None = None
    docs_url: str | None = None
    completed: bool = False
    completed_at: datetime | None = None
    skipped: bool = False
    skipped_at: datetime | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class OnboardingStateResponse(BaseModel):
    items: list[OnboardingStateRead]
    completed_count: int
    total_count: int
    setup_done: bool


class OnboardingActionRequest(BaseModel):
    key: str
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class OnboardingExampleRunResponse(BaseModel):
    success: bool
    example_id: str
    event_id: UUID
    timeline_url: str
    message: str
