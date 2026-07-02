from typing import Protocol

from app.events.models import EventRun
from app.execution.context import PipelineContext
from app.execution.result import StepResult
from app.execution.step import ExecutionStep


class ExecutionHook(Protocol):
    async def before_step(self, context: PipelineContext, step: ExecutionStep) -> None:
        ...

    async def after_step(self, context: PipelineContext, step: ExecutionStep, result: StepResult) -> None:
        ...

    async def on_error(self, context: PipelineContext, step: ExecutionStep, error: Exception) -> None:
        ...

    async def on_finish(self, context: PipelineContext, run: EventRun) -> None:
        ...
