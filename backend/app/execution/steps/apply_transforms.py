from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.transforms.engine import engine as transform_engine
from app.variables.paths import PathResolutionError, resolve_path
from app.variables.resolver import build_runtime_scope


class ApplyTransformsStep:
    name = "apply_transforms"
    display_name = "Apply Transforms"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = dict((context.current_step.step_config_json or {}).get("config") or {})
        chains = config.get("chains") if isinstance(config.get("chains"), list) else []
        if not chains:
            return StepResult.failed("TRANSFORM_INPUT_INVALID", "apply_transforms requires at least one chain", artifacts=[_error_artifact("TRANSFORM_INPUT_INVALID", "No transform chains configured")])
        variables_update: dict[str, Any] = {"payload": deepcopy(context.variables.get("payload") or {}), "steps": dict(context.variables.get("steps") or {})}
        traces: list[dict[str, Any]] = []
        for index, chain in enumerate(chains):
            if not isinstance(chain, dict):
                return StepResult.failed("TRANSFORM_INPUT_INVALID", f"Transform chain #{index + 1} must be an object", artifacts=[_error_artifact("TRANSFORM_INPUT_INVALID", f"Invalid chain #{index + 1}")])
            source = str(chain.get("source") or "")
            target = str(chain.get("target") or "")
            if not source or not target:
                return StepResult.failed("TRANSFORM_INPUT_INVALID", "Transform chain requires source and target", artifacts=[_error_artifact("TRANSFORM_INPUT_INVALID", "Missing source/target")])
            scope = _scope(context, variables_update)
            try:
                value = resolve_path(scope, source)
            except PathResolutionError as exc:
                return StepResult.failed("TRANSFORM_INPUT_INVALID", str(exc), artifacts=[_error_artifact("TRANSFORM_INPUT_INVALID", str(exc))])
            result = transform_engine.apply_chain(value, chain.get("transforms") or [], scope)
            traces.append({"source": source, "target": target, "input": value, "success": result.success, "output": result.value, "trace": [item.model_dump(mode="json") for item in result.trace], "error_code": result.error_code, "error_message": result.error_message})
            if not result.success:
                return StepResult.failed(result.error_code or "TRANSFORM_FAILED", result.error_message or "Transform failed", artifacts=[ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "transform_trace.json", {"chains": traces})])
            try:
                _set_target(variables_update, target, result.value)
            except ValueError as exc:
                return StepResult.failed("TRANSFORM_TARGET_INVALID", str(exc), artifacts=[ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "transform_trace.json", {"chains": traces})])
        step_id = str(config.get("step_id") or "apply_transforms")
        variables_update["steps"][step_id] = {"chains": traces}
        return StepResult.success("Transforms applied", artifacts=[ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "transform_trace.json", {"chains": traces})], variables_update=variables_update)


def _scope(context: PipelineContext, variables_update: dict[str, Any]) -> dict[str, Any]:
    variables = {**context.variables, **variables_update}
    payload = variables.get("payload") or {}
    return build_runtime_scope(request_body=payload, variables=variables, context={"event_id": str(context.event.id), "run_id": str(context.run.id), "correlation_id": context.correlation_id})


def _set_target(variables_update: dict[str, Any], path: str, value: Any) -> None:
    if path.startswith("variables."):
        _set_path(variables_update, path.removeprefix("variables."), value)
    elif path.startswith("payload.") or path.startswith("request.body."):
        payload = variables_update.setdefault("payload", {})
        _set_path(payload, path.removeprefix("payload.").removeprefix("request.body."), value)
    else:
        raise ValueError("Transform target must start with variables. or payload.")


def _set_path(target: dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in path.split(".") if part]
    if not parts:
        raise ValueError("Target path is empty")
    current = target
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def _error_artifact(code: str, message: str) -> ArtifactCreate:
    return ArtifactCreate(ArtifactType.ERROR_DETAILS.value, "transform_error.json", {"error_code": code, "error_message": message})
