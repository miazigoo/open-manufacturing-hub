from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import repository as connector_repository
from app.connectors.builtin.onec.odata import read_odata
from app.flow_builder.validator import validate_builder
from app.json_builder.engine import build_json_from_fields, build_json_from_template
from app.variables.paths import PathResolutionError, resolve_path
from app.variables.resolver import build_runtime_scope, render_template


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
                value = resolve_path(scope, str(step["path"]))
                variables[name] = value
                result = value
                request_preview = {"path": step["path"]}
            elif step_type == "odata_query":
                query = _odata_query(step, scope)
                request_preview = {"connection": step.get("connection"), "resource": step.get("resource"), "query": query}
                items = await _preview_odata_items(session, step, query, run_real_queries)
                result = _saved_odata_result(items, step)
                variables[str(step["save_as"])] = result
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
                result = render_template(step.get("body") or "{{response}}", scope)
                request_preview = {"body": step.get("body")}
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
        mock_odata = (connector.config_json or {}).get("mock_odata") or {}
        items = mock_odata.get(step.get("resource")) if isinstance(mock_odata, dict) else None
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    if not run_real_queries:
        return []
    if connector is None:
        raise ValueError(f"ODATA_CONNECTION_NOT_FOUND: {step.get('connection')}")
    result = await read_odata(connector.config_json, str(step.get("resource")), query)
    if not result.success:
        raise ValueError(result.error_message or result.error_code or "ODATA_QUERY_FAILED")
    return result.items


def _saved_odata_result(items: list[dict[str, Any]], step: dict[str, Any]) -> Any:
    if int(step.get("top") or 1) == 1:
        return items[0] if items else None
    return items


def _preview_error(step_id: str, exc: Exception) -> dict[str, Any]:
    if isinstance(exc, PathResolutionError):
        return {"step_id": step_id, "code": "VARIABLE_NOT_FOUND", "message": str(exc), "hint": "Check source path or add a previous Read Field/OData step."}
    return {"step_id": step_id, "code": exc.__class__.__name__.upper(), "message": str(exc), "hint": "Open this step and check its configuration."}
