from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ArtifactRead(BaseModel):
    id: UUID
    event_id: UUID
    run_id: UUID
    step_id: UUID | None
    artifact_type: str
    name: str
    content_json: dict[str, Any]
    content_hash: str
    size_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArtifactDiff(BaseModel):
    artifact_id: UUID
    compare_with: UUID
    added: dict[str, Any]
    removed: dict[str, Any]
    changed: dict[str, dict[str, Any]]
