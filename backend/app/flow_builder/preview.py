from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import repository as connector_repository
from app.connectors.builtin.onec.odata import read_odata
from app.flow_builder.validator import validate_builder
from app.json_builder.engine import build_json_from_fields, build_json_from_template
from app.business_rules.engine import engine as rules_engine
from app.transforms.engine import engine as transform_engine
from app.variables.paths import PathResolutionError, resolve_path
from app.variables.resolver import build_runtime_scope, render_template
from app.secrets.service import SecretResolver


async def preview_builder(session: AsyncSession, builder_json: dict[str, Any], sample_request: dict[str, Any], *, run_real_queries: bool = False) -> dict[str, Any]:
    validation = validate_builder(builder_json)
    if not validation["valid"]:
        return {"valid": False, "variables": {}, "steps": [], "final_payload_preview": None, "target_request_preview": None, "errors": validation["errors"]}
    variables: dict[str, Any] = {"steps": {}}
    steps_preview: list[dict[str, Any]] = []
    final_payload = None
    target_request = None
    for step in builder_json.get("steps") or []:
        step_id = str(step["id"])
        step_type = str(step["type"])
        scope = _scope(sample_request, variables)
        try:
            if step_type == "read_variable":
                name = str(step.get("save_as") or step.get("variable") or step.get("name"))
                path = str(step["path"])
                paths = [path, *[str(item).strip() for item in step.get("fallback_paths") or [] if str(item).strip()]]
                last_error: PathResolutionError | None = None
                for candidate in paths:
                    try:
                        value = resolve_path(scope, candidate)
                        path = candidate
                        break
                    except PathResolutionError as exc:
                        last_error = exc
                else:
                    raise last_error or PathResolutionError("Variable path not found")
                variables[name] = value
                result = value
                request_preview = {"path": path, "fallback_paths": step.get("fallback_paths") or []}
            elif step_type == "apply_transforms":
                result = _preview_apply_transforms(step, sample_request, variables)
                sample_request = result["payload"]
                variables.update(result["variables"])
                request_preview = {"chains": step.get("chains") or []}
            elif step_type == "evaluate_rules":
                rule_set = step.get("rules_json") if isinstance(step.get("rules_json"), dict) else {"mode": step.get("mode") or "first_match", "rules": step.get("rules") or [], "name": step.get("rule_set") or step.get("name")}
                rule_result = rules_engine.evaluate(rule_set, {"payload": sample_request, "variables": variables})
                variables.update(rule_result.variables)
                sample_request = rule_result.payload
                result = rule_result.model_dump(mode="json")
                request_preview = {"rule_set": step.get("rule_set"), "matched_rules": rule_result.matched_rules, "status": rule_result.status}
                if rule_result.status == "failed":
                    raise ValueError(rule_result.error_message or rule_result.error_code or "BUSINESS_RULE_FAILED")
            elif step_type == "odata_query":
                query = _odata_query(step, scope)
                request_preview = {"connection": step.get("connection"), "resource": step.get("resource"), "query": query}
                items = await _preview_odata_items(session, step, query, run_real_queries)
                result = _saved_odata_result(items, step)
                variables[str(step["save_as"])] = result
            elif step_type == "resolve_object":
                input_data = _resolve_input_preview(step.get("input") or {}, scope)
                result = _preview_resolved_object(step, input_data)
                save_as = str(step.get("save_as") or step.get("resolver") or step_id)
                variables[save_as] = result
                sample_request = _apply_injections(sample_request, step.get("inject") or {}, result, variables, save_as)
                request_preview = {"resolver_code": step.get("resolver_code") or step.get("resolver"), "input": input_data, "cache": step.get("use_cache", True)}
            elif step_type == "build_json":
                result = build_json_from_template(step["template"], scope) if step.get("template") else build_json_from_fields(step.get("fields") or [], scope)
                variables[str(step.get("save_as") or "target_payload")] = result
                final_payload = result
                request_preview = {"save_as": step.get("save_as") or "target_payload"}
            elif step_type == "call_endpoint":
                body = render_template(step.get("body") or "{{target_payload}}", scope)
                response = {"status_code": 200, "body": step.get("mock_response_json") or {"preview": True}}
                result = {"would_call": {"connector": step.get("connector"), "method": step.get("method", "POST"), "path": step.get("path"), "body": body}, "response": response}
                variables["response"] = response
                target_request = result["would_call"]
                request_preview = result["would_call"]
            elif step_type == "return_response":
                if step.get("body_template") is not None:
                    body = render_template(str(step.get("body_template") or ""), scope)
                else:
                    body = render_template(step.get("body") if step.get("body") is not None else "{{response}}", scope)
                result = {
                    "status_code": int(step.get("status_code") or 200),
                    "response_body_type": step.get("response_body_type") or ("json" if isinstance(body, dict) else "raw_text"),
                    "headers": step.get("headers") if isinstance(step.get("headers"), dict) else {},
                    "body": body,
                }
                request_preview = {"status_code": result["status_code"], "headers": result["headers"], "response_body_type": result["response_body_type"]}
            else:
                result = None
                request_preview = None
            variables.setdefault("steps", {})[step_id] = result if step_type != "odata_query" else {"items": result if isinstance(result, list) else [result] if result else [], "first": result}
            steps_preview.append({"id": step_id, "type": step_type, "name": step.get("name"), "status": "success", "request_preview": request_preview, "result_preview": result})
        except Exception as exc:
            steps_preview.append({"id": step_id, "type": step_type, "name": step.get("name"), "status": "failed", "error": _preview_error(step_id, exc)})
            return {"valid": False, "variables": variables, "steps": steps_preview, "final_payload_preview": final_payload, "target_request_preview": target_request, "errors": [_preview_error(step_id, exc)]}
    return {"valid": True, "variables": variables, "steps": steps_preview, "final_payload_preview": final_payload, "target_request_preview": target_request, "errors": []}


def _scope(sample_request: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    return build_runtime_scope(request_body=sample_request, variables=variables, headers={}, query={}, context={})


def _odata_query(step: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    query: dict[str, Any] = {}
    filter_value = step.get("filter") or _compile_filter_builder(step.get("filter_builder") or [], scope)
    if filter_value:
        query["$filter"] = render_template(filter_value, scope)
    if step.get("select"):
        query["$select"] = step["select"] if isinstance(step["select"], str) else ",".join(step["select"])
    if step.get("top"):
        query["$top"] = int(step["top"])
    if step.get("orderby"):
        query["$orderby"] = str(step["orderby"])
    return query


def _compile_filter_builder(conditions: list[dict[str, Any]], scope: dict[str, Any]) -> str:
    chunks = []
    for condition in conditions:
        field = str(condition.get("field") or "").strip()
        operator = str(condition.get("operator") or "eq")
        raw_value = render_template(condition.get("value"), scope)
        if not field or raw_value in (None, ""):
            continue
        value = str(raw_value).replace("'", "''")
        if operator in {"contains", "startswith", "endswith"}:
            chunks.append(f"{operator}({field}, '{value}')")
        else:
            chunks.append(f"{field} {operator} '{value}'")
    return " and ".join(chunks)


async def _preview_odata_items(session: AsyncSession, step: dict[str, Any], query: dict[str, Any], run_real_queries: bool) -> list[dict[str, Any]]:
    if isinstance(step.get("mock_items"), list):
        return [item for item in step["mock_items"] if isinstance(item, dict)]
    connector = await connector_repository.get_by_name(session, str(step.get("connection")))
    if connector is not None:
        connector_config = await SecretResolver(session).resolve_config(connector.config_json)
        mock_odata = (connector_config or {}).get("mock_odata") or {}
        items = mock_odata.get(step.get("resource")) if isinstance(mock_odata, dict) else None
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    if not run_real_queries:
        return []
    if connector is None:
        raise ValueError(f"ODATA_CONNECTION_NOT_FOUND: {step.get('connection')}")
    connector_config = await SecretResolver(session).resolve_config(connector.config_json)
    result = await read_odata(connector_config, str(step.get("resource")), query)
    if not result.success:
        raise ValueError(result.error_message or result.error_code or "ODATA_QUERY_FAILED")
    return result.items


def _saved_odata_result(items: list[dict[str, Any]], step: dict[str, Any]) -> Any:
    if int(step.get("top") or 1) == 1:
        return items[0] if items else None
    return items


def _preview_apply_transforms(step: dict[str, Any], sample_request: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    next_payload = dict(sample_request)
    next_variables = {key: value for key, value in variables.items() if key != "steps"}
    traces: list[dict[str, Any]] = []
    for chain in step.get("chains") or []:
        scope = _scope(next_payload, next_variables)
        value = resolve_path(scope, str(chain.get("source")))
        result = transform_engine.apply_chain(value, chain.get("transforms") or [], scope)
        if not result.success:
            raise ValueError(result.error_message or result.error_code or "TRANSFORM_FAILED")
        target = str(chain.get("target") or "")
        if target.startswith("payload.") or target.startswith("request.body."):
            _set_payload_path(next_payload, target, result.value)
        elif target.startswith("variables."):
            _set_variable_path(next_variables, target.removeprefix("variables."), result.value)
        else:
            raise ValueError("Transform target must start with payload. or variables.")
        traces.append({"source": chain.get("source"), "target": target, "value": result.value, "trace": [item.model_dump(mode="json") for item in result.trace]})
    return {"payload": next_payload, "variables": next_variables, "traces": traces}


def _set_variable_path(variables: dict[str, Any], path: str, value: Any) -> None:
    parts = [part for part in path.split(".") if part]
    current = variables
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    if parts:
        current[parts[-1]] = value


def _resolve_input_preview(value: Any, scope: dict[str, Any]) -> dict[str, Any]:
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
        if isinstance(raw, dict) and raw.get("source") is not None:
            source = str(raw.get("source") or "")
            try:
                value = render_template(source, scope) if "{{" in source else resolve_path(scope, source)
            except PathResolutionError:
                value = source
            transformed = transform_engine.apply_chain(value, raw.get("transforms") or [], scope)
            if not transformed.success:
                raise ValueError(transformed.error_message or transformed.error_code or "Resolver input transform failed")
            result[key] = transformed.value
    return result


def _preview_resolved_object(step: dict[str, Any], input_data: dict[str, Any]) -> dict[str, Any]:
    mock = step.get("mock_object")
    if isinstance(mock, dict):
        return dict(mock)
    resolver_code = str(step.get("resolver_code") or step.get("resolver") or "")
    object_type = str(step.get("object_type") or _object_type_from_resolver(resolver_code))
    key = next((value for value in input_data.values() if value not in (None, "")), "preview")
    base = {"object_type": object_type, "uuid": f"{object_type.lower()}-{key}", "name": f"{object_type} {key}"}
    if object_type == "Customer":
        base["inn"] = input_data.get("inn") or key
    if object_type == "Product":
        base["article"] = input_data.get("article") or input_data.get("code") or key
    if object_type == "Warehouse":
        base["code"] = input_data.get("code") or key
    return base


def _object_type_from_resolver(resolver_code: str) -> str:
    lowered = resolver_code.lower()
    if "customer" in lowered:
        return "Customer"
    if "product" in lowered:
        return "Product"
    if "warehouse" in lowered:
        return "Warehouse"
    if "printer" in lowered:
        return "PrintJob"
    if "order" in lowered:
        return "SalesOrder"
    return "BusinessObject"


def _apply_injections(sample_request: dict[str, Any], inject: Any, result: dict[str, Any], variables: dict[str, Any], save_as: str) -> dict[str, Any]:
    if not isinstance(inject, dict) or not inject:
        return sample_request
    next_payload = dict(sample_request)
    scope = _scope(next_payload, {**variables, save_as: result, "resolved": result, "object": result})
    for target, source in inject.items():
        source_path = str(source)
        try:
            value = render_template(source_path, scope) if "{{" in source_path else resolve_path(scope, source_path)
        except PathResolutionError:
            value = result.get(source_path)
        _set_payload_path(next_payload, str(target), value)
    return next_payload


def _set_payload_path(payload: dict[str, Any], path: str, value: Any) -> None:
    clean_path = path.removeprefix("payload.").removeprefix("request.body.")
    parts = [part for part in clean_path.split(".") if part]
    current = payload
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    if parts:
        current[parts[-1]] = value


def _preview_error(step_id: str, exc: Exception) -> dict[str, Any]:
    if isinstance(exc, PathResolutionError):
        return {"step_id": step_id, "code": "VARIABLE_NOT_FOUND", "message": str(exc), "hint": "Check source path or add a previous Read Field/OData step."}
    return {"step_id": step_id, "code": exc.__class__.__name__.upper(), "message": str(exc), "hint": "Open this step and check its configuration."}
