from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.enums import RunMode


@dataclass
class PipelineContext:
    payload: dict[str, Any]
    mode: RunMode
    start_from_step: str | None = None
    workflow_id: UUID | None = None
    data: dict[str, Any] = field(default_factory=dict)
