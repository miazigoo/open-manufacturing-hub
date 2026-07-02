from app.core.enums import ArtifactType
from app.core.errors import BadRequestError
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.mappings.engine import MappingEngine
from app.mappings.service import get_latest_version_by_mapping_name
from app.pipeline import steps as legacy_steps


class MapPayloadStep:
    name = "map_payload"
    display_name = "Map Payload"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        canonical = dict(context.variables.get("canonical_payload") or context.variables.get("payload") or {})
        try:
            mapping_name = ((context.current_step.step_config_json or {}).get("config") or {}).get("mapping") if context.current_step else None
            if mapping_name:
                mapping_version = await get_latest_version_by_mapping_name(context.session, str(mapping_name))
                if mapping_version is None:
                    return StepResult.failed("MAPPING_NOT_FOUND", f"Mapping {mapping_name} not found")
                mapped = MappingEngine().apply(canonical, mapping_version.rules_json)
            elif context.workflow and context.workflow.target_mapping_version is not None:
                mapped = MappingEngine().apply(canonical, context.workflow.target_mapping_version.rules_json)
            else:
                mapped = legacy_steps.map_to_target(canonical)
        except BadRequestError as exc:
            return StepResult.failed("MAPPING_FAILED", str(exc))
        return StepResult.success(
            "Payload mapped",
            artifacts=[ArtifactCreate(ArtifactType.MAPPED_PAYLOAD.value, "mapped_payload.json", mapped)],
            variables_update={"mapped_payload": mapped, "canonical_payload": mapped, "payload": mapped},
        )
