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
from app.xml_toolkit.paths import extract_fields
from app.xml_toolkit.renderer import render_xml_template
from app.xml_toolkit.service import raw_forward_preview


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
            elif step_type == "foreach":
                source_items = _collection(step.get("items"), scope)
                nested = step.get("step") or step.get("do") or {}
                if not isinstance(nested, dict) or nested.get("type") != "odata_query":
                    raise ValueError("Foreach currently supports nested odata_query")
                item_as = str(step.get("item_as") or "item")
                index_as = str(step.get("index_as") or "index")
                flatten = bool(step.get("flatten", True))
                combined: list[Any] = []
                iterations: list[dict[str, Any]] = []
                for index, item in enumerate(source_items):
                    iteration_scope = dict(scope)
                    iteration_scope[item_as] = item
                    iteration_scope[index_as] = index
                    iteration_scope["foreach"] = {"item": item, "index": index}
                    query = _odata_query(nested, iteration_scope)
                    resource = str(render_template(nested.get("resource") or "", iteration_scope))
                    nested_for_preview = dict(nested)
                    nested_for_preview["resource"] = resource
                    items = await _preview_odata_items(session, nested_for_preview, query, run_real_queries)
                    if flatten:
                        combined.extend(items)
                    else:
                        combined.append(_saved_odata_result(items, nested))
                    iterations.append({"index": index, "item": item, "resource": resource, "query": query, "items_count": len(items)})
                result = combined
                variables[str(step.get("save_as") or step_id)] = result
                request_preview = {"items": step.get("items"), "items_count": len(source_items), "item_as": item_as, "nested_type": nested.get("type")}
                variables.setdefault("steps", {})[step_id] = {"items": result, "iterations": iterations, "items_count": len(result), "source_items_count": len(source_items)}
            elif step_type == "print_labels":
                printer_selection = step.get("printer_selection") if isinstance(step.get("printer_selection"), dict) else {}
                labels_config = step.get("labels") if isinstance(step.get("labels"), dict) else {}
                labels = _collection(labels_config.get("path") or "request.body.labels", scope)
                if not labels:
                    raise ValueError("Массив labels пустой.")
                item_as = str(labels_config.get("item_as") or "label")
                selected_printer = _preview_printer_name(printer_selection, scope)
                template = str(step.get("zpl_template") or "")
                rendered_labels = [_render_print_label(template, scope, item, labels, item_as, index) for index, item in enumerate(labels)]
                print_job = {
                    "id": "PRINT-PREVIEW-001",
                    "status": "dry_run" if step.get("print_mode") == "dry_run" else "sent",
                    "labels_count": len(labels),
                }
                result = {
                    "success": True,
                    "print_job_id": print_job["id"],
                    "labels_count": len(labels),
                    "printer": selected_printer,
                    "status": print_job["status"],
                    "dry_run": step.get("print_mode") == "dry_run",
                }
                save_as = str(step.get("save_as") or "print_status")
                variables[save_as] = result
                variables["print_job"] = print_job
                variables["labels"] = {"items": labels, "length": len(labels)}
                variables["selected_printer"] = {"name": selected_printer}
                variables["rendered_zpl_labels"] = rendered_labels
                request_preview = {"printer": selected_printer, "labels_count": len(labels), "print_mode": step.get("print_mode") or "dry_run", "first_zpl": rendered_labels[0]}
            elif step_type == "marking_code_pool_export":
                order_number = _required_preview_text(scope, step.get("order_number_path"), "order_number_path")
                full_codes_base64 = _optional_preview_list(scope, step.get("full_codes_base64_path"))
                codes = _optional_preview_list(scope, step.get("codes_path"))
                if bool(full_codes_base64) == bool(codes):
                    raise ValueError("Pass exactly one of full_codes_base64_path or codes_path")
                result = {
                    "success": True,
                    "status": "preview",
                    "order_number": order_number,
                    "full_codes_base64_count": len(full_codes_base64 or []),
                    "codes_count": len(codes or []),
                    "allow_overwrite": step.get("allow_overwrite"),
                    "actions_override": step.get("actions_override") if isinstance(step.get("actions_override"), dict) else None,
                }
                save_as = str(step.get("save_as") or "marking_pool_export")
                variables[save_as] = result
                variables["marking_pool_export"] = result
                request_preview = {"will_save_local_outbox": True, "will_copy_laser_file": True, "will_forward_external": True}
            elif step_type == "xml_extract":
                raw_xml = _sample_xml(sample_request)
                fields = [field for field in step.get("fields") or [] if isinstance(field, dict)]
                values, errors = extract_fields(raw_xml, fields)
                if errors:
                    raise ValueError("; ".join(str(item.get("message")) for item in errors))
                variables.update(values)
                result = values
                request_preview = {"source": step.get("source") or "request.body_raw", "fields": fields}
            elif step_type == "raw_xml_forward":
                raw_xml = _sample_xml(sample_request)
                result = raw_forward_preview(raw_xml).model_dump(mode="json")
                target_request = {"body_type": "xml", "hash": result["input_sha256"], "forwarded_unchanged": result["forwarded_unchanged"]}
                request_preview = target_request
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
                result = {"would_call": {"connector": step.get("connector"), "method": step.get("method", "POST"), "url": step.get("url"), "path": step.get("path"), "body": body}, "response": response}
                variables["response"] = response
                target_request = result["would_call"]
                request_preview = result["would_call"]
            elif step_type in {"return_response", "build_xml_response"}:
                response_type = step.get("response_body_type") or ("xml" if step_type == "build_xml_response" else None)
                template = step.get("body_template") if step.get("body_template") is not None else step.get("template")
                if response_type == "xml" and template is not None:
                    body = render_xml_template(str(template or ""), scope)
                elif step.get("body_template") is not None:
                    body = render_template(str(step.get("body_template") or ""), scope)
                else:
                    body = render_template(step.get("body") if step.get("body") is not None else "{{response}}", scope)
                result = {
                    "status_code": int(step.get("status_code") or 200),
                    "response_body_type": response_type or ("json" if isinstance(body, dict) else "raw_text"),
                    "headers": step.get("headers") if isinstance(step.get("headers"), dict) else ({"Content-Type": "application/xml"} if response_type == "xml" else {}),
                    "body": body,
                }
                request_preview = {"status_code": result["status_code"], "headers": result["headers"], "response_body_type": result["response_body_type"]}
            else:
                result = None
                request_preview = None
            if step_type != "foreach":
                variables.setdefault("steps", {})[step_id] = result if step_type != "odata_query" else {"items": result if isinstance(result, list) else [result] if result else [], "first": result}
            steps_preview.append({"id": step_id, "type": step_type, "name": step.get("name"), "status": "success", "request_preview": request_preview, "result_preview": result})
        except Exception as exc:
            steps_preview.append({"id": step_id, "type": step_type, "name": step.get("name"), "status": "failed", "error": _preview_error(step_id, exc)})
            return {"valid": False, "variables": variables, "steps": steps_preview, "final_payload_preview": final_payload, "target_request_preview": target_request, "errors": [_preview_error(step_id, exc)]}
    return {"valid": True, "variables": variables, "steps": steps_preview, "final_payload_preview": final_payload, "target_request_preview": target_request, "errors": []}


def _scope(sample_request: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    return build_runtime_scope(
        request_body=sample_request,
        variables=variables,
        headers={},
        query={},
        raw_text=sample_request.get("text") if isinstance(sample_request, dict) else None,
        xml=sample_request.get("xml") if isinstance(sample_request, dict) else None,
        context={"event_id": "preview-event-id", "run_id": "preview-run-id", "correlation_id": "preview-correlation-id"},
    )


def _sample_xml(sample_request: dict[str, Any]) -> str:
    if isinstance(sample_request, dict):
        value = sample_request.get("xml") or sample_request.get("text") or sample_request.get("body_raw")
        if value:
            return str(value)
    raise ValueError("XML sample is empty. Paste a real XML request before preview.")


def _collection(value: Any, scope: dict[str, Any]) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        expression = value.strip()
        resolved = render_template(expression, scope) if "{{" in expression else resolve_path(scope, expression)
        if isinstance(resolved, list):
            return resolved
        if resolved is None:
            return []
        raise ValueError(f"Foreach items resolved to {type(resolved).__name__}, expected array")
    raise ValueError("Foreach items must be an array or a path/template string")


def _required_preview_text(scope: dict[str, Any], path: Any, label: str) -> str:
    value = _optional_preview_value(scope, path)
    if value in (None, ""):
        raise ValueError(f"{label} resolved to empty value")
    return str(value)


def _optional_preview_list(scope: dict[str, Any], path: Any) -> list[str] | None:
    value = _optional_preview_value(scope, path)
    if value in (None, ""):
        return None
    if not isinstance(value, list):
        raise ValueError(f"{path} resolved to {type(value).__name__}, expected array")
    return [str(item) for item in value if str(item)]


def _optional_preview_value(scope: dict[str, Any], path: Any) -> Any:
    if path in (None, ""):
        return None
    expression = str(path).strip()
    if not expression:
        return None
    return render_template(expression, scope) if "{{" in expression else resolve_path(scope, expression)


def _preview_printer_name(config: dict[str, Any], scope: dict[str, Any]) -> str:
    mode = str(config.get("mode") or "from_request")
    if mode == "fixed":
        return str(config.get("fixed_printer_name") or "").strip()
    if mode == "rule_based":
        raise ValueError("Выбор принтера по правилу будет добавлен позже.")
    value = resolve_path(scope, str(config.get("path") or "request.body.printer"))
    return str(value or "").strip()


def _render_print_label(template: str, scope: dict[str, Any], item: Any, labels: list[Any], item_as: str, index: int) -> str:
    label_scope = dict(scope)
    label_scope[item_as] = item
    label_scope["label"] = item
    label_scope["labels"] = {"items": labels, "length": len(labels)}
    label_scope["label_index"] = index
    return str(render_template(template, label_scope))


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
    if step.get("paginate") is False:
        connector_config = {**connector_config, "odata": {**(connector_config.get("odata") or {}), "max_pages": 1}}
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
