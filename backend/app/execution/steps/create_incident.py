from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.external_errors.service import link_incident_for_step
from app.incidents.service import safe_record_failure


class CreateIncidentStep:
    name = "create_incident"
    display_name = "Create Incident"

    async def can_execute(self, context: PipelineContext) -> bool:
        return not context.dry_run and context.metadata.get("failure_step") is not None

    async def execute(self, context: PipelineContext) -> StepResult:
        if not await self.can_execute(context):
            return StepResult.skipped("No failure to record")
        incident = await safe_record_failure(context.session, context.event, context.run, context.metadata["failure_step"])
        if incident is not None:
            await link_incident_for_step(context.session, step_id=context.metadata["failure_step"].id, incident_id=incident.id)
        content = {"incident_id": str(incident.id) if incident else None, "created": incident is not None}
        return StepResult.success(
            "Incident recorded" if incident else "Incident recording skipped after internal error",
            artifacts=[ArtifactCreate("incident", "incident.json", content)],
            variables_update={"incident_id": str(incident.id) if incident else None},
        )
