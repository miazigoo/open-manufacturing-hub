from __future__ import annotations

from typing import Any

from app.connectors import repository as connector_repository
from app.connectors.builtin.onec.odata import read_odata
from app.connectors.builtin.rest_connector import RESTConnector
from app.connectors.manager import ConnectorManager
from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.json_builder.engine import build_json_from_fields, build_json_from_template
from app.packages_training.mock_dnp import submit_marking_pool
from app.packages_training.mock_odata import query_mock_odata
from app.packages_training.mock_printer import print_label
from app.sdk.types import ConnectorContext
from app.secrets.service import SecretResolver
from app.variables.paths import PathResolutionError, resolve_path
from app.variables.resolver import build_runtime_scope, render_template
from app.xml_toolkit.renderer import render_xml_template


class FlowReadVariableStep:
    name = "flow_read_variable"
    display_name = "Read Field"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        variable_name = str(config.get("save_as") or config.get("variable") or config.get("name") or "").strip()
        path = str(config.get("path") or "").strip()
        paths = [path, *[str(item).strip() for item in config.get("fallback_paths") or [] if str(item).strip()]]
        last_error: PathResolutionError | None = None
        try:
            scope = _scope(context)
            for candidate in paths:
                try:
                    value = resolve_path(scope, candidate)
                    path = candidate
                    break
                except PathResolutionError as exc:
                    last_error = exc
            else:
                raise last_error or PathResolutionError("Variable path not found")
        except PathResolutionError as exc:
            return _failed("VARIABLE_NOT_FOUND", str(exc), config, "Check the request sample and the source path.")
        variables = _variables_with_step(context, config["step_id"], value)
        variables[variable_name] = value
        return StepResult.success(
            f"Read {variable_name}",
            artifacts=[ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "read_variable_result.json", {"name": variable_name, "path": path, "value": value})],
            variables_update=variables,
        )


class FlowODataQueryStep:
    name = "flow_odata_query"
    display_name = "OData Query"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        scope = _scope(context)
        query = _odata_query(config, scope)
        connector_name = str(config.get("connection") or "")
        try:
            resource = str(render_template(config.get("resource") or "", scope))
        except Exception as exc:
            return _failed("ODATA_RESOURCE_BUILD_FAILED", str(exc), config, "Check OData resource template and previous step variables.")
        request_artifact = ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "odata_query_request.json", {"connection": connector_name, "resource": resource, "query": query})
        connector = await connector_repository.get_by_name(context.session, connector_name)
        if connector is None:
            return _failed("ODATA_CONNECTION_NOT_FOUND", f"OData connection {connector_name} not found", config, "Create or select a 1C connector with OData enabled.", [request_artifact])
        if connector.connector_type != "onec":
            return _failed("ODATA_CONNECTION_NOT_FOUND", f"Connector {connector_name} is not a 1C/OData connector", config, "Select connector_type=onec.", [request_artifact])
        connector_config = await SecretResolver(context.session).resolve_config(connector.config_json)
        mock_items = _mock_odata_items(config, connector_config, query)
        if mock_items is not None:
            items = mock_items
            response_payload = {"mock": True, "value": items}
        else:
            result = await read_odata(connector_config, resource, query)
            response_payload = result.response_payload or {"items_count": len(result.items)}
            if not result.success:
                return _failed(result.error_code or "ODATA_QUERY_FAILED", result.error_message or "OData query failed", config, "Check OData resource, filter, credentials and 1C availability.", [request_artifact, ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "odata_query_response.json", _as_dict(response_payload))])
            items = result.items
        if not items and config.get("required", True):
            return _failed("ODATA_RESULT_EMPTY", f"OData step {config['step_id']} returned no rows", config, "Check source value, resource and filter.", [request_artifact, ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "odata_query_response.json", _as_dict(response_payload))])
        saved = items[0] if int(config.get("top") or 1) == 1 else items
        save_as = str(config.get("save_as") or config["step_id"])
        step_value = {"items": items, "first": items[0] if items else None, "query": query}
        variables = _variables_with_step(context, config["step_id"], step_value)
        variables[save_as] = saved
        return StepResult.success(
            "OData query complete",
            artifacts=[request_artifact, ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "odata_query_response.json", _as_dict(response_payload)), ArtifactCreate(ArtifactType.CANONICAL_PAYLOAD.value, "odata_query_result.json", {"save_as": save_as, "result": saved, "items_count": len(items)})],
            variables_update=variables,
        )


class FlowBuildJsonStep:
    name = "flow_build_json"
    display_name = "Build JSON"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        try:
            result = build_json_from_template(config["template"], _scope(context)) if config.get("template") else build_json_from_fields(config.get("fields") or [], _scope(context))
        except Exception as exc:
            return _failed("JSON_BUILD_FAILED", str(exc), config, "Check JSON field mappings and variable paths.")
        save_as = str(config.get("save_as") or "target_payload")
        variables = _variables_with_step(context, config["step_id"], result)
        variables[save_as] = result
        variables["mapped_payload"] = result
        return StepResult.success(
            "JSON payload built",
            artifacts=[ArtifactCreate(ArtifactType.MAPPED_PAYLOAD.value, "json_builder_template.json", {"template": config.get("template"), "fields": config.get("fields")}), ArtifactCreate(ArtifactType.MAPPED_PAYLOAD.value, "json_builder_result.json", result)],
            variables_update=variables,
        )


class FlowConditionStep:
    name = "flow_condition"
    display_name = "Condition"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        ok = _evaluate_condition(str(config.get("if") or ""), _scope(context))
        artifact = ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "condition_result.json", {"if": config.get("if"), "matched": ok})
        if ok or str(config.get("else") or "continue") == "continue":
            return StepResult.success("Condition passed", artifacts=[artifact])
        return _failed("CONDITION_FAILED", str(config.get("error_message") or "Condition failed"), config, "Check previous lookup results or adjust the condition.", [artifact])


class FlowCallEndpointStep:
    name = "flow_call_endpoint"
    display_name = "Call Endpoint"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        connector_name = str(config.get("connector") or context.target_system or "")
        direct_url = str(config.get("url") or "").strip()
        try:
            body = render_template(config.get("body") or "{{target_payload}}", _scope(context))
        except Exception as exc:
            return _failed("TARGET_BODY_BUILD_FAILED", str(exc), config, "Check call body variable path.")
        payload = body if isinstance(body, dict) else {"body": body}
        method = str(config.get("method") or "POST").upper()
        headers = config.get("headers") if isinstance(config.get("headers"), dict) else {}
        request_payload = {"connector": connector_name or None, "method": method, "url": direct_url or None, "path": config.get("path"), "headers": headers, "body": payload}
        request_artifact = ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "outgoing_request.json", request_payload)
        if direct_url:
            connector_context = ConnectorContext(event_id=context.event.id, run_id=context.run.id, step_id=context.current_step.id if context.current_step else None, correlation_id=context.correlation_id, source_system=context.source_system, target_system=direct_url, dry_run=context.dry_run, metadata={"step_name": config["step_id"], "url": direct_url, "method": method})
            connector_config = {"url": direct_url, "method": method, "headers": headers}
            result = await RESTConnector().dry_run_send(connector_config, payload, connector_context) if context.dry_run else await RESTConnector().send(connector_config, payload, connector_context)
            response = {"status_code": result.status_code, "body": result.response_payload or {}}
            variables = _variables_with_step(context, config["step_id"], {"request": result.request_payload or request_payload, "response": response})
            variables["response"] = response
            artifacts = [ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "outgoing_request.json", result.request_payload or request_payload)]
            if result.response_payload is not None:
                artifacts.append(ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "incoming_response.json", result.response_payload))
            if not result.success:
                return _failed(result.error_code or "TARGET_CALL_FAILED", result.error_message or "Target call failed", config, result.hint or "Check target URL and payload contract.", artifacts)
            return StepResult.success("Endpoint URL call complete", artifacts=artifacts, variables_update=variables)
        connector = await connector_repository.get_by_name(context.session, connector_name)
        if connector is None:
            return _failed("TARGET_CONNECTOR_NOT_FOUND", f"Target connector {connector_name} not found", config, "Create the target connector or select another one.", [request_artifact])
        training_response = _training_target_response(connector.config_json or {}, payload)
        if training_response is not None:
            status_code, response_body = training_response
            response = {"status_code": status_code, "body": response_body, "mock": True}
            variables = _variables_with_step(context, config["step_id"], {"request": request_payload, "response": response})
            variables["response"] = response
            artifacts = [request_artifact, ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "incoming_response.json", response)]
            if status_code >= 400:
                artifacts.append(ArtifactCreate(ArtifactType.EXTERNAL_ERROR.value, "external_error.json", response_body))
                return _failed(str(response_body.get("error") or "TRAINING_TARGET_FAILED"), str(response_body.get("message") or "Training target failed"), config, str(response_body.get("hint") or "Open timeline artifacts for the mock target response."), artifacts)
            return StepResult.success("Training mock call complete", artifacts=artifacts, variables_update=variables)
        mock_response = (connector.config_json or {}).get("mock_response_json") or config.get("mock_response_json")
        if mock_response is not None:
            response = {"status_code": 200, "body": mock_response, "mock": True}
            variables = _variables_with_step(context, config["step_id"], {"request": request_payload, "response": response})
            variables["response"] = response
            return StepResult.success("Endpoint mock call complete", artifacts=[request_artifact, ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "incoming_response.json", response)], variables_update=variables)
        manager = context.connector_manager or ConnectorManager(context.session)
        connector_context = ConnectorContext(event_id=context.event.id, run_id=context.run.id, step_id=context.current_step.id if context.current_step else None, correlation_id=context.correlation_id, source_system=context.source_system, target_system=connector_name, dry_run=context.dry_run, metadata={"step_name": config["step_id"], "path": config.get("path"), "method": request_payload["method"]})
        result = await manager.send_to_target(connector_name, payload, connector_context)
        response = {"status_code": result.status_code, "body": result.response_payload or {}}
        variables = _variables_with_step(context, config["step_id"], {"request": result.request_payload or request_payload, "response": response})
        variables["response"] = response
        artifacts = [ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "outgoing_request.json", result.request_payload or request_payload)]
        if result.response_payload is not None:
            artifacts.append(ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "incoming_response.json", result.response_payload))
        if not result.success:
            return _failed(result.error_code or "TARGET_CALL_FAILED", result.error_message or "Target call failed", config, result.hint or "Check target connector settings and payload contract.", artifacts)
        return StepResult.success("Endpoint call complete", artifacts=artifacts, variables_update=variables)


class FlowReturnResponseStep:
    name = "flow_return_response"
    display_name = "Return Response"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        try:
            scope = _scope(context)
            if str(config.get("response_body_type") or "").lower() == "xml" and config.get("body_template") is not None:
                body = render_xml_template(str(config.get("body_template") or ""), scope)
            elif config.get("body_template") is not None:
                body = render_template(str(config.get("body_template") or ""), scope)
            else:
                body = render_template(config.get("body") if config.get("body") is not None else "{{response}}", scope)
        except Exception as exc:
            return _failed("RETURN_RESPONSE_BUILD_FAILED", str(exc), config, "Check return body variable path.")
        body_type = str(config.get("response_body_type") or ("json" if isinstance(body, dict) else "raw_text"))
        status_code = int(config.get("status_code") or 200)
        headers = config.get("headers") if isinstance(config.get("headers"), dict) else {}
        response = {
            "success": True,
            "event_id": str(context.event.id),
            "run_id": str(context.run.id),
            "status_code": status_code,
            "response_body_type": body_type,
            "headers": headers,
            "body": body,
        }
        artifacts = [ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "return_response.json", response)]
        if body_type == "xml":
            artifacts.insert(0, ArtifactCreate(ArtifactType.MAPPED_PAYLOAD.value, "xml_response_template.xml", {"template": str(config.get("body_template") or "")}))
            artifacts.append(ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "xml_response_rendered.xml", {"xml": str(body)}))
        return StepResult.success("Response selected", artifacts=artifacts, variables_update={"response": response})


def _config(context: PipelineContext) -> dict[str, Any]:
    return dict((context.current_step.step_config_json or {}).get("config") or {})


def _scope(context: PipelineContext) -> dict[str, Any]:
    payload = context.variables.get("payload") or {}
    return build_runtime_scope(request_body=payload, variables=context.variables, headers=payload.get("_headers") if isinstance(payload, dict) else {}, query=payload.get("_query") if isinstance(payload, dict) else {}, raw_text=payload.get("text") if isinstance(payload, dict) else None, xml=payload.get("xml") if isinstance(payload, dict) else None, context={"event_id": str(context.event.id), "run_id": str(context.run.id), "correlation_id": context.correlation_id})


def _variables_with_step(context: PipelineContext, step_id: str, value: Any) -> dict[str, Any]:
    steps = dict(context.variables.get("steps") or {})
    steps[step_id] = value
    return {"steps": steps}


def _odata_query(config: dict[str, Any], scope: dict[str, Any]) -> dict[str, Any]:
    query: dict[str, Any] = {}
    filter_value = config.get("filter") or _compile_filter_builder(config.get("filter_builder") or [], scope)
    if filter_value:
        query["$filter"] = render_template(filter_value, scope)
    if config.get("select"):
        query["$select"] = config["select"] if isinstance(config["select"], str) else ",".join(config["select"])
    if config.get("top"):
        query["$top"] = int(config["top"])
    if config.get("orderby"):
        query["$orderby"] = str(config["orderby"])
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
        elif value.lower() in {"true", "false"}:
            chunks.append(f"{field} {operator} {value.lower()}")
        else:
            chunks.append(f"{field} {operator} '{value}'")
    return " and ".join(chunks)


def _mock_odata_items(config: dict[str, Any], connector_config: dict[str, Any], query: dict[str, Any]) -> list[dict[str, Any]] | None:
    if isinstance(config.get("mock_items"), list):
        return [item for item in config["mock_items"] if isinstance(item, dict)]
    mock_odata = (connector_config or {}).get("mock_odata") or {}
    if not isinstance(mock_odata, dict) or not mock_odata:
        return None
    response = query_mock_odata(mock_odata, str(config.get("resource") or ""), query)
    items = response.get("value")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else None


def _training_target_response(connector_config: dict[str, Any], payload: dict[str, Any]) -> tuple[int, dict[str, Any]] | None:
    if connector_config.get("training_mock_dnp"):
        return submit_marking_pool(payload)
    if connector_config.get("training_mock_printer"):
        return print_label(payload)
    return None


def _evaluate_condition(expression: str, scope: dict[str, Any]) -> bool:
    expression = expression.strip()
    if expression.endswith(" exists"):
        path = expression.removesuffix(" exists").strip()
        value = render_template(path, scope) if path.startswith("{{") else resolve_path(scope, path)
        return value not in (None, "", [], {})
    value = render_template(expression, scope)
    return bool(value)


def _failed(code: str, message: str, config: dict[str, Any], hint: str, artifacts: list[ArtifactCreate] | None = None) -> StepResult:
    step_id = str(config.get("step_id") or "builder_step")
    return StepResult.failed(code, message, artifacts=artifacts or [ArtifactCreate(ArtifactType.ERROR_DETAILS.value, "builder_step_error.json", {"step_id": step_id, "error_code": code, "error_message": message, "hint": hint})], human_title=f"Builder step {step_id} failed", human_summary=message, developer_message=f"Step {step_id}: {message}", hint=hint)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {"value": value}
