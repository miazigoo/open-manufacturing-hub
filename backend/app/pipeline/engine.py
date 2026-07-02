from sqlalchemy.ext.asyncio import AsyncSession

from app.events.models import EventRun, IntegrationEvent
from app.execution.engine import ExecutionEngine
from app.pipeline.context import PipelineContext


class PipelineEngine:
    """Compatibility adapter. New code should use app.execution.engine.ExecutionEngine."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def run(self, event: IntegrationEvent, run: EventRun, context: PipelineContext) -> EventRun:
        return await ExecutionEngine(self.session).execute_event(
            event.id,
            mode=context.mode,
            start_from_step=context.start_from_step,
            initial_payload=context.payload,
            workflow_id=context.workflow_id,
        )
