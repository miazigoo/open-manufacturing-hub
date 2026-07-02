from typing import Any

from pydantic import BaseModel


class ReplayFromStepRequest(BaseModel):
    step_name: str


class EditReplayRequest(BaseModel):
    edited_content: dict[str, Any]
    start_from_step: str = "validate"
