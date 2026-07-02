from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult


class SendNotificationsStep:
    name = "send_notifications"
    display_name = "Send Notifications"

    async def can_execute(self, context: PipelineContext) -> bool:
        return not context.dry_run and context.metadata.get("failure_step") is not None

    async def execute(self, context: PipelineContext) -> StepResult:
        if not await self.can_execute(context):
            return StepResult.skipped("No notification trigger")
        # Incident service owns notification delivery and cooldown handling; this step makes the failure workflow explicit.
        content = {"incident_id": context.variables.get("incident_id"), "delivery_owner": "incident_service"}
        return StepResult.success(
            "Notifications delegated to incident service",
            artifacts=[ArtifactCreate("notification_dispatch", "notification_dispatch.json", content)],
        )
