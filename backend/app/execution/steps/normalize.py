from app.core.enums import ArtifactType
from app.core.errors import BadRequestError
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.mappings.engine import MappingEngine
from app.pipeline import steps as legacy_steps


class NormalizePayloadStep:
    name = "normalize"
    display_name = "Normalize Payload"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        raw_payload = dict(context.variables.get("raw_payload") or context.variables.get("payload") or {})
        try:
            if context.workflow and context.workflow.source_mapping_version is not None:
                canonical = MappingEngine().apply(raw_payload, context.workflow.source_mapping_version.rules_json)
            else:
                canonical = legacy_steps.normalize(raw_payload)
        except BadRequestError as exc:
            return StepResult.failed("MAPPING_FAILED", str(exc))
        return StepResult.success(
            "Payload normalized",
            artifacts=[ArtifactCreate(ArtifactType.CANONICAL_PAYLOAD.value, "canonical_payload.json", canonical)],
            variables_update={"canonical_payload": canonical, "payload": canonical},
        )
