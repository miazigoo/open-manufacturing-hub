from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult


class ReceiveEventStep:
    name = "receive"
    display_name = "Receive Event"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        payload = dict(context.variables.get("raw_payload") or context.variables.get("payload") or {})
        artifacts = [ArtifactCreate(ArtifactType.RAW_PAYLOAD.value, "raw_payload.json", payload)]
        if isinstance(payload.get("_route_match_trace"), dict):
            artifacts.append(
                ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "route_match_trace.json", payload["_route_match_trace"])
            )
        return StepResult.success(
            "Payload received",
            artifacts=artifacts,
            variables_update={"raw_payload": payload, "payload": payload},
        )
