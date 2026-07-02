from typing import Protocol

from app.execution.context import PipelineContext
from app.execution.result import StepResult


class ExecutionStep(Protocol):
    name: str
    display_name: str

    async def execute(self, context: PipelineContext) -> StepResult:
        ...

    async def can_execute(self, context: PipelineContext) -> bool:
        ...
