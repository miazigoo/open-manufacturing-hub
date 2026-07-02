from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.pipeline import steps as legacy_steps


class HandleResponseStep:
    name = "handle_response"
    display_name = "Handle Response"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        response = context.variables.get("response") or {"status_code": 204}
        handled = legacy_steps.handle_response(response)
        return StepResult.success(
            "Response handled",
            artifacts=[ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "handled_response.json", handled)],
            variables_update={"handled_response": handled},
        )
