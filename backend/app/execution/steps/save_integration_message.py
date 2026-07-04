from __future__ import annotations

from uuid import UUID

from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.onec_workbench.models import IntegrationMessage


class SaveIntegrationMessageStep:
    name = "save_integration_message"
    display_name = "Save Integration Message"

    async def can_execute(self, context: PipelineContext) -> bool:
        return isinstance(context.variables.get("payload"), dict) and bool(context.variables["payload"].get("message_id"))

    async def execute(self, context: PipelineContext) -> StepResult:
        message_id = context.variables["payload"].get("message_id")
        message = await context.session.get(IntegrationMessage, UUID(str(message_id)))
        if message is None:
            return StepResult.failed("INTEGRATION_MESSAGE_NOT_FOUND", f"Integration message {message_id} not found")
        content = {
            "message_id": str(message.id),
            "status": message.status.value,
            "source_system": message.source_system,
            "target_system": message.target_system,
            "message_type": message.message_type,
            "payload_sha256": message.payload_sha256,
            "payload_size_bytes": message.payload_size_bytes,
        }
        return StepResult.success("Integration message linked", artifacts=[ArtifactCreate("integration_message", "integration_message.json", content)], variables_update={"message": content})
