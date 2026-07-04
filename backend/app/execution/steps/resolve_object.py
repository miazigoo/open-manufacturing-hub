from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.resolvers.engine import ResolverEngine
from app.variables.paths import PathResolutionError, resolve_path
from app.variables.resolver import build_runtime_scope, render_template


class ResolveObjectStep:
    name = "resolve_object"
    display_name = "Resolve Business Object"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = dict((context.current_step.step_config_json or {}).get("config") or {})
        resolver_code = str(config.get("resolver_code") or config.get("resolver") or "").strip()
        if not resolver_code:
            return _failed("RESOLVER_CODE_REQUIRED", "Resolve Business Object step requires resolver_code", config)
        scope = _scope(context)
        try:
            input_data = _resolve_input(config.get("input") or config.get("input_data") or {}, scope)
        except Exception as exc:
            return _failed("RESOLVER_INPUT_BUILD_FAILED", str(exc), config)
        engine = ResolverEngine(context.session)
        result = await engine.resolve(resolver_code, input_data, context=_resolver_context(context), use_cache=bool(config.get("use_cache", True)))
        artifacts = [_artifact_from_resolver(item) for item in result.artifacts]
        artifacts.insert(0, ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "resolver_step_config.json", {"resolver_code": resolver_code, "save_as": config.get("save_as"), "required": config.get("required", True)}))
        variables = _variables_with_step(context, str(config.get("step_id") or resolver_code), {"input": input_data, "result": result.model_dump(mode="json")})
        if result.success and result.object_json:
            save_as = str(config.get("save_as") or config.get("variable") or resolver_code)
            variables[save_as] = result.object_json
            payload = _payload_with_injections(context.variables.get("payload") or {}, config.get("inject") or {}, result.object_json, scope, save_as)
            if payload is not None:
                variables["payload"] = payload
            return StepResult.success(
                f"Resolved {result.object_type}",
                artifacts=artifacts,
                variables_update=variables,
                metadata={"resolver_code": resolver_code, "object_type": result.object_type, "cache_status": result.cache_status},
            )
        if config.get("required", True):
            return StepResult.failed(
                result.error_code or "OBJECT_RESOLVE_FAILED",
                result.error_message or "Business object was not resolved",
                artifacts=artifacts,
                variables_update=variables,
                metadata={"resolver_code": resolver_code, "object_type": result.object_type, "cache_status": result.cache_status},
                human_title="Business object resolve failed",
                human_summary=result.error_message or "Resolver did not return a canonical object.",
                developer_message=f"Resolver {resolver_code} failed with {result.error_code}",
                hint="Check resolver input, cache state, connector settings and source data.",
            )
        return StepResult.success(
            f"Resolver {resolver_code} returned no object",
            artifacts=artifacts,
            variables_update=variables,
            metadata={"resolver_code": resolver_code, "object_type": result.object_type, "cache_status": result.cache_status},
        )


def _scope(context: PipelineContext) -> dict[str, Any]:
    payload = context.variables.get("payload") or {}
    return build_runtime_scope(request_body=payload, variables=context.variables, headers=payload.get("_headers") if isinstance(payload, dict) else {}, query=payload.get("_query") if isinstance(payload, dict) else {}, raw_text=payload.get("text") if isinstance(payload, dict) else None, xml=payload.get("xml") if isinstance(payload, dict) else None, context={"event_id": str(context.event.id), "run_id": str(context.run.id), "correlation_id": context.correlation_id})


def _resolver_context(context: PipelineContext) -> dict[str, Any]:
    return {"event_id": str(context.event.id), "run_id": str(context.run.id), "correlation_id": context.correlation_id, "source_system": context.source_system, "target_system": context.target_system}


def _resolve_input(value: Any, scope: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Resolver input must be a JSON object")
    result: dict[str, Any] = {}
    for key, raw in value.items():
        if isinstance(raw, str):
            if "{{" in raw:
                result[key] = render_template(raw, scope)
            else:
                try:
                    result[key] = resolve_path(scope, raw)
                except PathResolutionError:
                    result[key] = raw
        else:
            result[key] = render_template(raw, scope)
    return result


def _variables_with_step(context: PipelineContext, step_id: str, value: Any) -> dict[str, Any]:
    steps = dict(context.variables.get("steps") or {})
    steps[step_id] = value
    return {"steps": steps}


def _payload_with_injections(payload: Any, inject: Any, object_json: dict[str, Any], scope: dict[str, Any], save_as: str) -> dict[str, Any] | None:
    if not isinstance(inject, dict) or not inject:
        return None
    next_payload = deepcopy(payload if isinstance(payload, dict) else {})
    object_scope = {**scope, save_as: object_json, "resolved": object_json, "object": object_json}
    for target_path, source_path in inject.items():
        source = str(source_path)
        try:
            value = render_template(source, object_scope) if "{{" in source else resolve_path(object_scope, source)
        except PathResolutionError:
            value = object_json.get(source)
        _set_payload_path(next_payload, str(target_path), value)
    return next_payload


def _set_payload_path(payload: dict[str, Any], path: str, value: Any) -> None:
    clean_path = path.removeprefix("payload.").removeprefix("request.body.")
    parts = [part for part in clean_path.split(".") if part]
    if not parts:
        return
    current = payload
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    current[parts[-1]] = value


def _artifact_from_resolver(item: Any) -> ArtifactCreate:
    payload = item.payload if hasattr(item, "payload") else {}
    artifact_type = item.type if hasattr(item, "type") else ArtifactType.VALIDATION_RESULT.value
    name = item.name if hasattr(item, "name") else "resolver_artifact.json"
    return ArtifactCreate(str(artifact_type), str(name), payload if isinstance(payload, dict) else {"value": payload})


def _failed(code: str, message: str, config: dict[str, Any]) -> StepResult:
    step_id = str(config.get("step_id") or "resolve_object")
    return StepResult.failed(
        code,
        message,
        artifacts=[ArtifactCreate(ArtifactType.ERROR_DETAILS.value, "resolver_step_error.json", {"step_id": step_id, "error_code": code, "error_message": message})],
        human_title="Resolver step configuration error",
        human_summary=message,
        developer_message=f"Step {step_id}: {message}",
        hint="Open the Resolve Business Object block and check resolver code and input mapping.",
    )
