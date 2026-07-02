from app.core.enums import ArtifactType
from app.core.errors import BadRequestError
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.mappings.engine import MappingEngine
from app.pipeline import steps as legacy_steps


class MapPayloadStep:
    name = "map_payload"
    display_name = "Map Payload"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        canonical = dict(context.variables.get("canonical_payload") or context.variables.get("payload") or {})
        try:
            if context.workflow and context.workflow.target_mapping_version is not None:
                mapped = MappingEngine().apply(canonical, context.workflow.target_mapping_version.rules_json)
            else:
                mapped = legacy_steps.map_to_target(canonical)
        except BadRequestError as exc:
            return StepResult.failed("MAPPING_FAILED", str(exc))
        return StepResult.success(
            "Payload mapped",
            artifacts=[ArtifactCreate(ArtifactType.MAPPED_PAYLOAD.value, "mapped_payload.json", mapped)],
            variables_update={"mapped_payload": mapped},
        )
