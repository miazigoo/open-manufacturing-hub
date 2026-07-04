from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

BuilderStepType = Literal["read_variable", "odata_query", "build_json", "condition", "call_endpoint", "return_response"]


class FlowStep(BaseModel):
    id: str
    type: BuilderStepType
    name: str | None = None
    save_as: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}
