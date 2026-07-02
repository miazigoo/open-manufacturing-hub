from typing import Any

from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.execution.workflow import DEFAULT_VALIDATION
from app.mappings.engine import get_path


class ValidatePayloadStep:
    name = "validate"
    display_name = "Validate Payload"

    async def can_execute(self, context: PipelineContext) -> bool:
        return True

    async def execute(self, context: PipelineContext) -> StepResult:
        payload = context.variables.get("canonical_payload") or context.variables.get("payload") or {}
        result = self._validate(payload, context.workflow.validation_json if context.workflow else DEFAULT_VALIDATION)
        artifact = ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "validation_result.json", result)
        if not result["valid"]:
            return StepResult.failed("VALIDATION_FAILED", f"Missing fields: {', '.join(result['missing'])}", artifacts=[artifact])
        return StepResult.success("Payload valid", artifacts=[artifact])

    @staticmethod
    def _validate(payload: Any, validation: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {"valid": False, "missing": ["payload_object"], "errors": ["Payload must be an object"]}
        missing = [path for path in validation.get("required_fields", []) if get_path(payload, path) in (None, "")]
        errors: list[str] = []
        if "items" in payload and not isinstance(payload["items"], list):
            errors.append("items must be a list")
        if "warehouse_id" in payload and not isinstance(payload["warehouse_id"], str):
            errors.append("warehouse_id must be a string")
        return {"valid": not missing and not errors, "missing": missing, "errors": errors}
