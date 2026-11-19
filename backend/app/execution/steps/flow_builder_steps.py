from __future__ import annotations

import dataclasses
import json
import re
import xml.etree.ElementTree as ElementTree
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select

from app.connectors import repository as connector_repository
from app.connectors.builtin.onec.client import join_url
from app.connectors.builtin.onec.odata import read_odata
from app.connectors.builtin.rest_connector import RESTConnector
from app.connectors.manager import ConnectorManager
from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult, StepResultStatus
from app.integration_master.payload_renderer import PayloadRenderError, render_payload_step, render_xml_template as render_payload_xml_template
from app.integration_master.schemas import PayloadStepConfig
from app.json_builder.engine import build_json_from_fields, build_json_from_template
from app.operation_catalog.testers import evaluate_success_condition, extract_response

import httpx

from app.marking_code_pools import service as marking_code_pool_service
from app.marking_code_pools.schemas import MarkingCodePoolActionOverrides, OneCMarkingCodePoolExportRequest
from app.matchers.engine import evaluate_matcher_group
from app.packages_training.mock_dnp import submit_marking_pool
from app.packages_training.mock_external_api import import_order
from app.packages_training.mock_onec_http import accept_shipment_fact, save_order_external_id
from app.packages_training.mock_odata import query_mock_odata
from app.packages_training.mock_printer import print_label
from app.packages_training.mock_site import import_order_to_site
from app.sdk.types import ConnectorContext
from app.secrets.service import SecretResolver
from app.variables.paths import PathResolutionError, resolve_path
from app.variables.resolver import build_runtime_scope, render_template


class ODataStepError(RuntimeError):
    def __init__(self, code: str, message: str, hint: str, response_payload: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.response_payload = response_payload or {}


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
        try:
            items, response_payload = await _read_odata_items(context, config, query, resource)
        except ODataStepError as exc:
            return _failed(exc.code, exc.message, config, exc.hint, [request_artifact, ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "odata_query_response.json", _as_dict(exc.response_payload))])
        if not items and config.get("required", True):
            return _failed("ODATA_RESULT_EMPTY", f"OData step {config['step_id']} returned no rows", config, "Check source value, resource and filter.", [request_artifact, ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "odata_query_response.json", _as_dict(response_payload))])
        saved = _saved_odata_value(items, config)
        save_as = str(config.get("save_as") or config["step_id"])
        step_value = {"items": items, "first": items[0] if items else None, "query": query}
        variables = _variables_with_step(context, config["step_id"], step_value)
        variables[save_as] = saved
        return StepResult.success(
            "OData query complete",
            artifacts=[request_artifact, ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "odata_query_response.json", _as_dict(response_payload)), ArtifactCreate(ArtifactType.CANONICAL_PAYLOAD.value, "odata_query_result.json", {"save_as": save_as, "result": saved, "items_count": len(items)})],
            variables_update=variables,
        )


class FlowForEachStep:
    name = "flow_foreach"
    display_name = "For Each"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        scope = _scope(context)
        try:
            source_items = _collection(config.get("items"), scope)
        except Exception as exc:
            return _failed("FOREACH_ITEMS_BUILD_FAILED", str(exc), config, "Check foreach items path. It must resolve to an array.")

        nested = config.get("step") or config.get("do") or {}
        nested_type = nested.get("type") if isinstance(nested, dict) else None
        if nested_type not in FOREACH_NESTED_TYPES:
            return _failed(
                "FOREACH_STEP_UNSUPPORTED",
                f"Foreach supports nested steps: {', '.join(sorted(FOREACH_NESTED_TYPES))}",
                config,
                "Set step.type to odata_query, call_endpoint, build_json or extract.",
            )

        item_as = str(config.get("item_as") or "item")
        index_as = str(config.get("index_as") or "index")
        save_as = str(config.get("save_as") or config["step_id"])
        flatten = bool(config.get("flatten", True))
        continue_on_error = bool(config.get("continue_on_error", False))
        limits = config.get("limits") if isinstance(config.get("limits"), dict) else {}
        max_items = _positive_int(limits.get("max_items"), len(source_items))
        max_requests = _positive_int(limits.get("max_requests"), len(source_items))
        max_result_rows = _positive_int(limits.get("max_result_rows"), 0)

        if len(source_items) > max_items:
            return _failed(
                "FOREACH_MAX_ITEMS_EXCEEDED",
                f"Foreach source has {len(source_items)} items, max_items={max_items}",
                config,
                "Increase max_items only if this integration is expected to process that many source rows.",
            )
        if len(source_items) > max_requests:
            return _failed(
                "FOREACH_MAX_REQUESTS_EXCEEDED",
                f"Foreach needs {len(source_items)} OData requests, max_requests={max_requests}",
                config,
                "Increase max_requests or reduce the source array before foreach.",
            )

        combined: list[Any] = []
        iterations: list[dict[str, Any]] = []
        artifacts: list[ArtifactCreate] = [
            ArtifactCreate(
                ArtifactType.VALIDATION_RESULT.value,
                "foreach_input.json",
                {"items_path": config.get("items"), "items_count": len(source_items), "item_as": item_as},
            )
        ]
        errors: list[dict[str, Any]] = []

        for index, item in enumerate(source_items):
            iteration_scope = dict(scope)
            iteration_scope[item_as] = item
            iteration_scope[index_as] = index
            iteration_scope["foreach"] = {"item": item, "index": index}
            try:
                if nested_type == "odata_query":
                    query = _odata_query(nested, iteration_scope)
                    resource = str(render_template(nested.get("resource") or "", iteration_scope))
                    nested_config = dict(nested)
                    nested_config["resource"] = resource
                    items, response_payload = await _read_odata_items(context, nested_config, query, resource)
                    if not items and nested.get("required", True):
                        raise ValueError(f"Nested OData query returned no rows for item #{index + 1}")
                    result_value: Any = items if flatten else _saved_odata_value(items, nested)
                    if flatten:
                        combined.extend(items)
                    else:
                        combined.append(result_value)
                    if max_result_rows and len(combined) > max_result_rows:
                        return _failed(
                            "FOREACH_MAX_RESULT_ROWS_EXCEEDED",
                            f"Foreach result has more than max_result_rows={max_result_rows} rows",
                            config,
                            "For large code pools keep $top=500, enable pagination, and increase max_result_rows deliberately.",
                            artifacts,
                        )
                    iterations.append(
                        {
                            "index": index,
                            "item": item,
                            "resource": resource,
                            "query": query,
                            "items_count": len(items),
                        }
                    )
                    artifacts.append(
                        ArtifactCreate(
                            ArtifactType.OUTGOING_REQUEST.value,
                            f"foreach_{index + 1}_odata_request.json",
                            {"connection": nested.get("connection"), "resource": resource, "query": query},
                        )
                    )
                    artifacts.append(
                        ArtifactCreate(
                            ArtifactType.INCOMING_RESPONSE.value,
                            f"foreach_{index + 1}_odata_response.json",
                            _as_dict(response_payload),
                        )
                    )
                else:
                    nested_value, nested_artifacts = await _run_foreach_nested(nested_type, nested, context, item_as, index_as, item, index)
                    combined.append(nested_value)
                    iterations.append({"index": index, "item": item, "nested_type": nested_type})
                    artifacts.extend(nested_artifacts)
            except Exception as exc:
                error = {"index": index, "item": item, "error": str(exc)}
                errors.append(error)
                if not continue_on_error:
                    artifacts.append(ArtifactCreate(ArtifactType.ERROR_DETAILS.value, "foreach_error.json", {"errors": errors}))
                    return _failed("FOREACH_ITERATION_FAILED", str(exc), config, "Open foreach artifacts and check the failed item/resource/filter.", artifacts)

        step_value = {
            "items": combined,
            "iterations": iterations,
            "items_count": len(combined),
            "source_items_count": len(source_items),
            "errors": errors,
        }
        variables = _variables_with_step(context, config["step_id"], step_value)
        variables[save_as] = combined
        return StepResult.success(
            "Foreach complete",
            artifacts=[
                *artifacts,
                ArtifactCreate(
                    ArtifactType.CANONICAL_PAYLOAD.value,
                    "foreach_result.json",
                    {"save_as": save_as, "items_count": len(combined), "source_items_count": len(source_items), "errors": errors},
                ),
            ],
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


class FlowBuildPayloadStep:
    name = "flow_build_payload"
    display_name = "Build Payload"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        try:
            payload_config = PayloadStepConfig(**{key: value for key, value in config.items() if key not in {"step_id", "step_type", "display_name"}})
            result = render_payload_step(payload_config, _scope(context))
        except PayloadRenderError as exc:
            return _failed(exc.code, exc.message, config, "Check Payload Builder mappings and available variables.")
        except Exception as exc:
            return _failed("PAYLOAD_BUILD_FAILED", str(exc), config, "Check Payload Builder configuration.")

        save_as = str(config.get("save_as") or "target_payload")
        variables = _variables_with_step(context, config["step_id"], result.rendered_body)
        variables[save_as] = result.rendered_body
        variables["mapped_payload"] = result.rendered_body
        artifacts = [
            ArtifactCreate(ArtifactType.MAPPED_PAYLOAD.value, "payload_builder_config.json", {"body_type": config.get("body_type"), "json_mode": config.get("json_mode"), "save_as": save_as}),
            ArtifactCreate(ArtifactType.MAPPED_PAYLOAD.value, "payload_builder_result.json", {"body": result.rendered_body, "size_bytes": result.size_bytes, "warnings": result.warnings}),
        ]
        if config.get("response_artifacts"):
            template_name, rendered_name = _response_artifact_names(str(config.get("body_type") or "raw_text"))
            artifacts.extend(
                [
                    ArtifactCreate(ArtifactType.MAPPED_PAYLOAD.value, template_name, {"template": config.get("template"), "body_type": config.get("body_type")}),
                    ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, rendered_name, {"body": result.rendered_body, "size_bytes": result.size_bytes}),
                ]
            )
        return StepResult.success("Payload built", artifacts=artifacts, variables_update=variables)


class FlowConditionStep:
    name = "flow_condition"
    display_name = "Condition"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        scope = _scope(context)
        matcher_group = config.get("matcher_group")
        try:
            if matcher_group is not None:
                evaluation = evaluate_matcher_group(matcher_group, _matcher_context_from_scope(scope))
                ok = bool(evaluation["matched"])
                detail: dict[str, Any] = {"matcher_group": matcher_group, "matched": ok, "trace": evaluation["trace"]}
            else:
                ok = _evaluate_condition(str(config.get("if") or ""), scope)
                detail = {"if": config.get("if"), "matched": ok}
        except Exception as exc:
            return _failed(
                "CONDITION_EVALUATION_FAILED",
                str(exc),
                config,
                "Check previous step variables and condition path.",
            )
        artifact = ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "condition_result.json", detail)
        else_action = str(config.get("else") or "continue")
        if ok or else_action == "continue":
            return StepResult.success("Condition passed" if ok else "Condition not matched, continuing", artifacts=[artifact])
        if else_action == "skip":
            requested = [str(step) for step in config.get("skip_steps") or []]
            current = [str(step) for step in context.variables.get("skip_steps") or []]
            merged = list(dict.fromkeys([*current, *requested]))
            return StepResult.success(
                f"Condition not matched, skipping steps: {', '.join(requested) or 'none'}",
                artifacts=[artifact],
                variables_update={"skip_steps": merged},
            )
        return _failed("CONDITION_FAILED", str(config.get("error_message") or "Condition failed"), config, "Check previous lookup results or adjust the condition.", [artifact])


def _matcher_context_from_scope(scope: dict[str, Any]) -> dict[str, Any]:
    request = scope.get("request") or {}
    return {
        "body": scope,
        "text": request.get("raw_text") or "",
        "xml": request.get("xml") or "",
        "headers": request.get("headers") or {},
        "query": request.get("query") or {},
    }


class FlowExtractStep:
    name = "flow_extract"
    display_name = "Extract Fields"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        scope = _scope(context)
        source_path = str(config.get("source") or "request.body")
        try:
            source_value = resolve_path(scope, source_path)
        except Exception as exc:
            return _failed("EXTRACT_SOURCE_FAILED", str(exc), config, "Check the extract source path, e.g. request.body or steps.send_target.response.")
        fields = config.get("fields") or []
        if not isinstance(fields, list) or not fields:
            return _failed("EXTRACT_FIELDS_REQUIRED", "Extract step needs at least one field", config, "Add fields with name + path or regex.")
        extracted: dict[str, Any] = {}
        missing: list[str] = []
        traces: list[dict[str, Any]] = []
        for field in fields:
            if not isinstance(field, dict):
                continue
            name = str(field.get("name") or "").strip()
            if not name:
                continue
            try:
                value, found = _extract_field(field, source_value, scope, source_path)
            except Exception as exc:
                return _failed("EXTRACT_FIELD_FAILED", f"{name}: {exc}", config, "Check the field path or regex.")
            traces.append({"name": name, "found": found, "value": value})
            if found:
                extracted[name] = value
            elif field.get("required", True):
                missing.append(name)
        artifact = ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "extract_result.json", {"source": source_path, "fields": traces})
        if missing:
            return _failed("EXTRACT_FIELD_MISSING", f"Required fields not found: {', '.join(missing)}", config, "Open extract_result.json artifact and fix the paths/regex.", [artifact])
        variables = _variables_with_step(context, config["step_id"], extracted)
        variables.update(extracted)
        return StepResult.success("Fields extracted", artifacts=[artifact], variables_update=variables)


def _extract_field(field: dict[str, Any], source_value: Any, scope: dict[str, Any], source_path: str) -> tuple[Any, bool]:
    pattern = field.get("regex")
    if pattern:
        text = source_value if isinstance(source_value, str) else json.dumps(source_value, ensure_ascii=False, default=str)
        matches = list(re.finditer(str(pattern), text))
        if not matches:
            return None, False
        group = int(field.get("group") or 1)

        def group_value(match: re.Match[str]) -> str:
            return match.group(group) if match.re.groups >= group else match.group(0)

        if str(field.get("mode") or "first") == "all":
            return [group_value(match) for match in matches], True
        return group_value(matches[0]), True
    sub_path = str(field.get("path") or "").strip()
    if not sub_path:
        return source_value, source_value is not None
    try:
        value = resolve_path(scope, f"{source_path}.{sub_path}")
    except Exception:
        return None, False
    return value, value is not None


class FlowFilterArrayStep:
    name = "flow_filter_array"
    display_name = "Filter Array"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        scope = _scope(context)
        items_path = str(config.get("items") or "").strip()
        if not items_path:
            return _failed("FILTER_ITEMS_REQUIRED", "Filter step needs an items path", config, "Example: request.body.rows or steps.lookup.items.")
        try:
            value = resolve_path(scope, items_path)
        except Exception as exc:
            return _failed("FILTER_ITEMS_FAILED", str(exc), config, "Check the items path.")
        if not isinstance(value, list):
            return _failed("FILTER_ITEMS_NOT_ARRAY", f"Path {items_path} did not resolve to an array", config, "Point items to an array value.")
        where = config.get("where") or {"mode": "all", "rules": [{"type": "always"}]}
        passed: list[Any] = []
        dropped = 0
        for index, item in enumerate(value):
            matched = evaluate_matcher_group(where, {"body": {"item": item, "index": index}})["matched"]
            if matched:
                passed.append(item)
            else:
                dropped += 1
        save_as = str(config.get("save_as") or config["step_id"])
        step_value = {"items": passed, "passed": len(passed), "dropped": dropped, "source_count": len(value)}
        variables = _variables_with_step(context, config["step_id"], step_value)
        variables[save_as] = passed
        return StepResult.success(
            f"Filter kept {len(passed)} of {len(value)} items",
            artifacts=[
                ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "filter_result.json", {"items_path": items_path, "where": where, "passed": len(passed), "dropped": dropped}),
                ArtifactCreate(ArtifactType.CANONICAL_PAYLOAD.value, "filter_items.json", {"save_as": save_as, "items": passed}),
            ],
            variables_update=variables,
        )


class FlowBuildXmlStep:
    name = "flow_build_xml"
    display_name = "Build XML"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        scope = _scope(context)
        template = str(config.get("body_template") or config.get("template") or "")
        if not template.strip():
            return _failed("XML_TEMPLATE_EMPTY", "Build XML step needs a body_template", config, "Add an XML template with {{variables}}.")
        try:
            rendered = render_payload_xml_template(template, scope)
        except PayloadRenderError as exc:
            return _failed("XML_NOT_WELL_FORMED", str(exc), config, "Escape special characters in values or fix the template structure.")
        except Exception as exc:
            return _failed("XML_RENDER_FAILED", str(exc), config, "Check template variables against previous steps.")
        try:
            ElementTree.fromstring(rendered)
        except ElementTree.ParseError as exc:
            artifact = ArtifactCreate(ArtifactType.ERROR_DETAILS.value, "xml_rendered_invalid.txt", {"rendered": rendered[:4000]})
            return _failed("XML_NOT_WELL_FORMED", f"Rendered XML is not well-formed: {exc}", config, "Escape special characters in values or fix the template structure.", [artifact])
        save_as = str(config.get("save_as") or config["step_id"])
        variables = _variables_with_step(context, config["step_id"], {"xml": rendered})
        variables[save_as] = rendered
        return StepResult.success(
            "XML built",
            artifacts=[ArtifactCreate(ArtifactType.MAPPED_PAYLOAD.value, "built_xml.txt", {"save_as": save_as, "xml": rendered[:4000]})],
            variables_update=variables,
        )


class FlowCallOperationStep:
    name = "flow_call_operation"
    display_name = "Call Operation"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        scope = _scope(context)
        operation_ref = str(config.get("operation") or "").strip()
        if not operation_ref:
            return _failed("OPERATION_NOT_SET", "Call operation step needs an operation code or id", config, "Select an operation from Operation Catalog.")
        operation = await _load_operation(context.session, operation_ref)
        if operation is None:
            return _failed("OPERATION_NOT_FOUND", f"Operation {operation_ref} not found", config, "Check the operation code in Operation Catalog.")
        if not operation.enabled:
            return _failed("OPERATION_DISABLED", f"Operation {operation.name} is disabled", config, "Enable the operation in Operation Catalog.")
        try:
            url, headers, body_value, body_type = _operation_request(operation, config, scope)
        except Exception as exc:
            return _failed("OPERATION_REQUEST_BUILD_FAILED", str(exc), config, "Check the operation request template and input overrides.")
        method = str(operation.method or "POST").upper()
        timeout = float(operation.timeout_seconds or 30)
        request_artifact = ArtifactCreate(
            ArtifactType.OUTGOING_REQUEST.value,
            "operation_request.json",
            {"operation": operation.code, "method": method, "url": url, "headers": headers, "body_type": body_type, "body": body_value},
        )
        if context.dry_run:
            response_body = operation.sample_response_json if operation.sample_response_json is not None else {"dry_run": True}
            return _operation_success_result(context, config, operation, request_artifact, 200, response_body, dry_run=True)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if body_type in {"raw_text", "xml"}:
                    response = await client.request(method, url, content=str(body_value or ""), headers=headers)
                else:
                    response = await client.request(method, url, json=body_value, headers=headers)
        except httpx.HTTPError as exc:
            return _failed("OPERATION_CALL_FAILED", f"{operation.name} request failed: {exc}", config, "Check the connection profile URL and network.", [request_artifact])
        try:
            response_body: Any = response.json()
        except ValueError:
            response_body = response.text
        condition = evaluate_success_condition(operation.success_condition_json, response.status_code, response_body)
        response_artifact = ArtifactCreate(
            ArtifactType.INCOMING_RESPONSE.value,
            "operation_response.json",
            {"status_code": response.status_code, "body": response_body, "success_condition": condition.model_dump()},
        )
        if not condition.success:
            return _failed(
                "OPERATION_SUCCESS_CONDITION_FAILED",
                f"{operation.name} returned HTTP {response.status_code} and failed the success condition: {'; '.join(condition.errors) or response.text[:300]}",
                config,
                "Open operation_response.json and compare with the success condition in Operation Catalog.",
                [request_artifact, response_artifact],
            )
        return _operation_success_result(context, config, operation, request_artifact, response.status_code, response_body, extra_artifacts=[response_artifact])


async def _load_operation(session, ref: str) -> Any:
    from app.operation_catalog.models import OperationProfile

    try:
        from uuid import UUID as _UUID

        operation = await session.get(OperationProfile, _UUID(ref))
        if operation is not None:
            return operation
    except (ValueError, TypeError):
        pass
    result = await session.execute(select(OperationProfile).where(OperationProfile.code == ref).limit(1))
    return result.scalar_one_or_none()


def _operation_request(operation: Any, config: dict[str, Any], scope: dict[str, Any]) -> tuple[str, dict[str, str], Any, str]:
    overrides = config.get("input_overrides")
    if isinstance(overrides, dict) and overrides:
        body_value = build_json_from_template(overrides, scope)
        body_type = "json"
    elif operation.request_template_json is not None:
        body_value = build_json_from_template(operation.request_template_json, scope)
        body_type = "json"
    elif operation.request_template_text is not None:
        body_value = render_template(operation.request_template_text, scope)
        body_type = str(operation.body_type or "raw_text")
    else:
        body_value = render_template(config.get("body") or "{{target_payload}}", scope)
        body_type = str(operation.body_type or "json")
    url = str(render_template(operation.full_url or "", scope)).strip()
    if not url:
        path = str(render_template(operation.path or "", scope)).strip()
        url = path
    headers = {str(key): str(value) for key, value in (operation.headers_json or {}).items()}
    if body_type == "xml":
        headers.setdefault("Content-Type", "application/xml")
    elif body_type == "json":
        headers.setdefault("Content-Type", "application/json")
    return url, headers, body_value, body_type


def _operation_success_result(
    context: PipelineContext,
    config: dict[str, Any],
    operation: Any,
    request_artifact: ArtifactCreate,
    status_code: int,
    response_body: Any,
    *,
    dry_run: bool = False,
    extra_artifacts: list[ArtifactCreate] | None = None,
) -> StepResult:
    extracted, extractor_errors = extract_response(operation.response_extractors_json or [], response_body)
    artifacts = [request_artifact, *(extra_artifacts or [])]
    if dry_run:
        artifacts.append(ArtifactCreate(ArtifactType.DRY_RUN_REQUEST.value, "operation_dry_run.json", {"status_code": status_code, "body": response_body, "sample": True}))
    if extractor_errors:
        artifacts.append(ArtifactCreate(ArtifactType.ERROR_DETAILS.value, "operation_extractor_errors.json", {"errors": extractor_errors}))
        return _failed(
            "OPERATION_EXTRACT_FAILED",
            f"{operation.name} response extractors failed: {'; '.join(extractor_errors)}",
            config,
            "Check response extractors paths in Operation Catalog.",
            artifacts,
        )
    variables = _variables_with_step(context, config["step_id"], {"status_code": status_code, "response": response_body, "extracted": extracted, "dry_run": dry_run})
    save_as = str(config.get("save_response_as") or "").strip()
    if save_as:
        variables[save_as] = response_body
        variables[f"{save_as}_http"] = {"status_code": status_code, "body": response_body}
    variables.update(extracted)
    return StepResult.success(
        f"Operation {operation.name} complete" + (" (dry-run)" if dry_run else ""),
        artifacts=artifacts,
        variables_update=variables,
    )


class FlowCallEndpointStep:
    name = "flow_call_endpoint"
    display_name = "Call Endpoint"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        connector_name = str(config.get("connector") or context.target_system or "")
        scope = _scope(context)
        try:
            direct_url = str(render_template(str(config.get("url") or ""), scope) or "").strip()
            rendered_path = str(render_template(str(config.get("path") or ""), scope) or "").strip()
            body = render_template(config.get("body") or "{{target_payload}}", scope)
        except Exception as exc:
            return _failed("TARGET_BODY_BUILD_FAILED", str(exc), config, "Check call body variable path.")
        payload = body if isinstance(body, dict) else {"body": body}
        method = str(config.get("method") or "POST").upper()
        headers = config.get("headers") if isinstance(config.get("headers"), dict) else {}
        request_payload = {"connector": connector_name or None, "method": method, "url": direct_url or None, "path": rendered_path or None, "headers": headers, "body": payload}
        request_artifact = ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "outgoing_request.json", request_payload)
        if direct_url:
            mock_response = config.get("mock_response_json")
            if context.dry_run and mock_response is not None:
                response = {"status_code": 200, "body": mock_response, "mock": True, "dry_run": True}
                variables = _endpoint_variables(context, config, request_payload, response, mock_response)
                return StepResult.success(
                    "Endpoint URL dry-run complete",
                    artifacts=[request_artifact, ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "incoming_response.json", response)],
                    variables_update=variables,
                )
            connector_context = ConnectorContext(event_id=context.event.id, run_id=context.run.id, step_id=context.current_step.id if context.current_step else None, correlation_id=context.correlation_id, source_system=context.source_system, target_system=direct_url, dry_run=context.dry_run, metadata={"step_name": config["step_id"], "url": direct_url, "method": method})
            connector_config = {"url": direct_url, "method": method, "headers": headers}
            result = await RESTConnector().dry_run_send(connector_config, payload, connector_context) if context.dry_run else await RESTConnector().send(connector_config, payload, connector_context)
            response = {"status_code": result.status_code, "body": result.response_payload or {}}
            response_body = _endpoint_response_body(response)
            variables = _endpoint_variables(context, config, result.request_payload or request_payload, response, response_body)
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
            variables = _endpoint_variables(context, config, request_payload, response, response_body)
            artifacts = [request_artifact, ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "incoming_response.json", response)]
            if status_code >= 400:
                artifacts.append(ArtifactCreate(ArtifactType.EXTERNAL_ERROR.value, "external_error.json", response_body))
                return _failed(str(response_body.get("error") or "TRAINING_TARGET_FAILED"), str(response_body.get("message") or "Training target failed"), config, str(response_body.get("hint") or "Open timeline artifacts for the mock target response."), artifacts)
            return StepResult.success("Training mock call complete", artifacts=artifacts, variables_update=variables)
        mock_response = (connector.config_json or {}).get("mock_response_json") or config.get("mock_response_json")
        if mock_response is not None:
            response = {"status_code": 200, "body": mock_response, "mock": True}
            variables = _endpoint_variables(context, config, request_payload, response, mock_response)
            return StepResult.success("Endpoint mock call complete", artifacts=[request_artifact, ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "incoming_response.json", response)], variables_update=variables)
        manager = context.connector_manager or ConnectorManager(context.session)
        connector_context = ConnectorContext(event_id=context.event.id, run_id=context.run.id, step_id=context.current_step.id if context.current_step else None, correlation_id=context.correlation_id, source_system=context.source_system, target_system=connector_name, dry_run=context.dry_run, metadata={"step_name": config["step_id"], "path": rendered_path, "method": request_payload["method"]})
        if connector.connector_type == "rest" and rendered_path:
            connector_config = await SecretResolver(context.session).resolve_config(connector.config_json or {})
            base_url = str(connector_config.get("base_url") or connector_config.get("url") or "").strip()
            connector_config = {**connector_config, "url": join_url(base_url, rendered_path), "method": method, "headers": headers or connector_config.get("headers") or {}}
            result = await RESTConnector().dry_run_send(connector_config, payload, connector_context) if context.dry_run else await RESTConnector().send(connector_config, payload, connector_context)
            response = {"status_code": result.status_code, "body": result.response_payload or {}}
            response_body = _endpoint_response_body(response)
            variables = _endpoint_variables(context, config, result.request_payload or request_payload, response, response_body)
            artifacts = [ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "outgoing_request.json", result.request_payload or request_payload)]
            if result.response_payload is not None:
                artifacts.append(ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "incoming_response.json", result.response_payload))
            if not result.success:
                return _failed(result.error_code or "TARGET_CALL_FAILED", result.error_message or "Target call failed", config, result.hint or "Check target connector settings and step path.", artifacts)
            return StepResult.success("REST endpoint call complete", artifacts=artifacts, variables_update=variables)
        result = await manager.send_to_target(connector_name, payload, connector_context)
        response = {"status_code": result.status_code, "body": result.response_payload or {}}
        response_body = _endpoint_response_body(response)
        variables = _endpoint_variables(context, config, result.request_payload or request_payload, response, response_body)
        artifacts = [ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "outgoing_request.json", result.request_payload or request_payload)]
        if result.response_payload is not None:
            artifacts.append(ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "incoming_response.json", result.response_payload))
        if not result.success:
            return _failed(result.error_code or "TARGET_CALL_FAILED", result.error_message or "Target call failed", config, result.hint or "Check target connector settings and payload contract.", artifacts)
        return StepResult.success("Endpoint call complete", artifacts=artifacts, variables_update=variables)


class FlowPrintLabelsStep:
    name = "flow_print_labels"
    display_name = "Print Labels"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        scope = _scope(context)
        labels_config = config.get("labels") if isinstance(config.get("labels"), dict) else {}
        printer_config = config.get("printer_selection") if isinstance(config.get("printer_selection"), dict) else {}
        item_as = str(labels_config.get("item_as") or "label")
        required_fields = [str(item).strip() for item in labels_config.get("required_fields") or ["code"] if str(item).strip()]

        try:
            labels = _collection(labels_config.get("path") or "request.body.labels", scope)
        except Exception:
            return _failed("PRINT_LABELS_MISSING", "В запросе нет массива labels[].", config, "Проверьте путь labels array, например request.body.labels.")
        if not labels:
            return _failed("PRINT_LABELS_EMPTY", "Массив labels пустой.", config, "Передайте хотя бы одну строку labels[].")
        for index, item in enumerate(labels):
            if not isinstance(item, dict):
                return _failed("PRINT_LABEL_INVALID", f"labels[{index}] должен быть объектом.", config, "Каждая строка labels[] должна быть JSON object.")
            for field in required_fields:
                if item.get(field) in (None, ""):
                    if field == "code":
                        message = f"В labels[{index}] нет поля code. Нечего печатать в DataMatrix."
                    else:
                        message = f"В labels[{index}] нет обязательного поля {field}."
                    return _failed("PRINT_LABEL_FIELD_MISSING", message, config, "Проверьте sample request и required fields.")

        selected_printer, printer_error = _selected_printer_name(printer_config, scope)
        if printer_error:
            return _failed("PRINT_PRINTER_SELECTION_FAILED", printer_error, config, "Проверьте поле request.body.printer или fixed printer.")
        if not selected_printer:
            return _failed("PRINT_PRINTER_REQUIRED", "Принтер не выбран.", config, "Передайте printer в request или выберите fixed printer.")

        template = str(config.get("zpl_template") or "")
        rendered: list[str] = []
        try:
            for index, item in enumerate(labels):
                rendered.append(_render_label_zpl(template, scope, item, labels, item_as, index))
        except PathResolutionError as exc:
            return _failed("PRINT_ZPL_VARIABLE_MISSING", _friendly_zpl_missing(exc.path, labels_config), config, "Проверьте переменные в ZPL-шаблоне.")
        except Exception as exc:
            return _failed("PRINT_ZPL_RENDER_FAILED", str(exc), config, "Проверьте ZPL-шаблон и переменные.")
        for index, zpl in enumerate(rendered):
            if "^XA" not in zpl or "^XZ" not in zpl:
                return _failed("PRINT_ZPL_INVALID", f"ZPL для labels[{index}] должен содержать ^XA и ^XZ.", config, "Проверьте ZPL template.")

        print_mode = str(config.get("print_mode") or "dry_run")
        dry_run = context.dry_run or print_mode == "dry_run"
        limit = 1 if print_mode == "test_one_label" else len(labels)
        all_zpl = "\n".join(rendered)
        incoming_request = context.variables.get("payload") or {}
        artifacts = [
            ArtifactCreate(ArtifactType.RAW_PAYLOAD.value, "incoming_print_request.json", _as_dict(incoming_request)),
            ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "selected_printer.json", {"name": selected_printer, "selection": printer_config}),
            ArtifactCreate(ArtifactType.MAPPED_PAYLOAD.value, "zpl_template.zpl", {"template": template}),
            ArtifactCreate(ArtifactType.MAPPED_PAYLOAD.value, "rendered_zpl_first_label.zpl", {"zpl": rendered[0]}),
            ArtifactCreate(ArtifactType.MAPPED_PAYLOAD.value, "rendered_zpl_all_labels.zpl", {"zpl": all_zpl, "labels_count": len(rendered)}),
        ]

        target = await _find_print_target(context, selected_printer)
        if target is None:
            artifacts.append(ArtifactCreate(ArtifactType.ERROR_DETAILS.value, "printer_lookup_error.json", {"printer": selected_printer}))
            return _failed(
                "PRINT_PRINTER_NOT_FOUND",
                f"Принтер {selected_printer} не найден. Проверьте Printer connector или поле request.body.printer.",
                config,
                "Создайте PrintPrinter/ZPL connector или установите Training Sandbox.",
                artifacts,
            )

        if target.get("kind") == "training_mock":
            request_payload = {"printer": selected_printer, "zpl": all_zpl, "labels_count": len(labels), "dry_run": dry_run, "mode": print_mode}
            status_code, printer_response = print_label(request_payload)
            artifacts.extend(
                [
                    ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "printer_request.json", request_payload),
                    ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "printer_response.json", printer_response),
                ]
            )
            if status_code >= 400 or printer_response.get("success") is False:
                artifacts.append(ArtifactCreate(ArtifactType.EXTERNAL_ERROR.value, "external_error.json", printer_response))
                return _failed(
                    str(printer_response.get("error_code") or printer_response.get("error") or "PRINTER_UNAVAILABLE"),
                    str(printer_response.get("error_message") or printer_response.get("message") or "Принтер недоступен."),
                    config,
                    str(printer_response.get("hint") or "Проверьте IP, порт, сеть и питание принтера."),
                    artifacts,
                )
            print_job = {"id": printer_response.get("job_id") or "TRAIN-PRINT-001", "status": printer_response.get("status") or ("dry_run" if dry_run else "sent")}
            status = _normalized_print_status(print_job, selected_printer, labels, dry_run=dry_run, printer_response=printer_response)
            save_as = str(config.get("save_as") or "print_status")
            variables = _print_variables(context, config["step_id"], status, print_job, selected_printer, labels, rendered, save_as, printer_response)
            return StepResult.success("Print labels complete", artifacts=artifacts, variables_update=variables)

        from app.printing import service as printing_service
        from app.printing.schemas import PrintBatchRequest, PrintJobCreate, PrintJobLineCreate

        printer = target["printer"]
        job_key = _job_key(scope, context)
        lines = [
            PrintJobLineCreate(sequence_no=_sequence_no(item, index), code=str(item.get("code")), zpl=rendered[index])
            for index, item in enumerate(labels)
        ]
        request_payload = {
            "job_key": job_key,
            "printer": selected_printer,
            "printer_id": str(printer.id),
            "source_system": context.source_system or "OMH",
            "dry_run": dry_run,
            "limit": limit,
            "lines_count": len(lines),
        }
        artifacts.append(ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "printer_request.json", request_payload))
        try:
            job = await printing_service.create_job(
                context.session,
                PrintJobCreate(
                    job_key=job_key,
                    printer_id=printer.id,
                    source_system=context.source_system or "OMH",
                    source_document_id=str((context.variables.get("payload") or {}).get("job_key") or job_key),
                    source_document_name=str((context.variables.get("payload") or {}).get("operation") or "print_labels"),
                    label_settings_json={"pattern": "request_print", "print_mode": print_mode, "dry_run": dry_run},
                    lines=lines,
                ),
            )
            batch = await printing_service.send_batch(context.session, job.id, PrintBatchRequest(limit=limit, dry_run=dry_run))
        except Exception as exc:
            artifacts.append(ArtifactCreate(ArtifactType.ERROR_DETAILS.value, "printer_response.json", {"success": False, "error_message": str(exc)}))
            return _failed("PRINT_SEND_FAILED", str(exc), config, "Принтер недоступен. Проверьте IP, порт, сеть и питание принтера.", artifacts)

        response_payload = {
            "job": {"id": str(batch.job.id), "status": batch.job.status.value if hasattr(batch.job.status, "value") else str(batch.job.status)},
            "processed": batch.processed,
            "sent": batch.sent,
            "failed": batch.failed,
            "dry_run": batch.dry_run,
            "results": [
                {
                    "sequence_no": item.sequence_no,
                    "status": item.status.value if hasattr(item.status, "value") else str(item.status),
                    "success": item.success,
                    "error_code": item.error_code,
                    "error_message": item.error_message,
                }
                for item in batch.results
            ],
        }
        artifacts.append(ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "printer_response.json", response_payload))
        if batch.failed:
            artifacts.append(ArtifactCreate(ArtifactType.EXTERNAL_ERROR.value, "external_error.json", response_payload))
            first_error = next((item for item in batch.results if not item.success), None)
            return _failed(
                first_error.error_code if first_error else "PRINTER_UNAVAILABLE",
                first_error.error_message if first_error else "Принтер недоступен.",
                config,
                "Проверьте IP, порт, сеть и питание принтера.",
                artifacts,
            )
        print_job = {"id": str(batch.job.id), "status": batch.job.status.value if hasattr(batch.job.status, "value") else str(batch.job.status)}
        status = _normalized_print_status(print_job, selected_printer, labels, dry_run=dry_run, printer_response=response_payload)
        save_as = str(config.get("save_as") or "print_status")
        variables = _print_variables(context, config["step_id"], status, print_job, selected_printer, labels, rendered, save_as, response_payload)
        return StepResult.success("Print labels complete", artifacts=artifacts, variables_update=variables)


class FlowMarkingCodePoolExportStep:
    name = "flow_marking_code_pool_export"
    display_name = "CHZ Marking Code Pool Export"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        scope = _scope(context)
        try:
            request = _marking_code_pool_request(config, scope, context)
        except Exception as exc:
            return _failed(
                "MARKING_POOL_REQUEST_BUILD_FAILED",
                str(exc),
                config,
                "Проверьте пути order_number_path/full_codes_base64_path в настройках шага.",
            )

        request_summary = _marking_pool_request_summary(request)
        request_artifact = ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "marking_code_pool_export_request.json", request_summary)

        if context.dry_run:
            try:
                preview = await marking_code_pool_service.preview_onec_pool_export(context.session, request)
            except Exception as exc:
                return _failed(
                    "MARKING_POOL_PREVIEW_FAILED",
                    str(exc),
                    config,
                    "Проверьте номер заказа, Base64-коды и настройки CHZ delivery.",
                    [request_artifact],
                )
            preview_payload = preview.model_dump(mode="json") if hasattr(preview, "model_dump") else dict(preview)
            status = {"success": True, "status": "dry_run", "preview": preview_payload}
            variables = _variables_with_step(context, config["step_id"], status)
            _store_marking_pool_variables(variables, config, status)
            return StepResult.dry_run(
                "CHZ marking code pool export preview complete",
                artifacts=[
                    request_artifact,
                    ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "marking_code_pool_export_preview.json", preview_payload),
                ],
                variables_update=variables,
            )

        try:
            record, dnp_forward = await marking_code_pool_service.export_onec_pool_to_file(context.session, request)
        except Exception as exc:
            return _failed(
                "MARKING_POOL_EXPORT_FAILED",
                str(exc),
                config,
                "Проверьте кодировку full_codes_base64, доступность SMB-папки и DNP endpoint.",
                [request_artifact],
            )

        metadata = record.metadata_json or {}
        response_meta = metadata.get("response") if isinstance(metadata.get("response"), dict) else {}
        actions = metadata.get("actions") if isinstance(metadata.get("actions"), dict) else {}
        success = bool(response_meta.get("success", record.status != "failed"))
        response_payload = {
            "success": success,
            "status": str(response_meta.get("status") or record.status),
            "message": f"Accepted {record.total_codes} marking codes as {record.file_name}; status={record.status}",
            "warnings": list(response_meta.get("warnings") or []),
            "export": {
                "id": str(record.id),
                "order_number": record.order_number,
                "file_name": record.file_name,
                "file_path": record.file_path,
                "total_codes": record.total_codes,
                "content_sha256": record.content_sha256,
                "status": record.status,
                "error_message": record.error_message,
            },
            "actions": actions,
            "external_forward": dnp_forward,
            "dnp_forward": dnp_forward,
        }
        variables = _variables_with_step(context, config["step_id"], response_payload)
        _store_marking_pool_variables(variables, config, response_payload)
        variables["response"] = {"status_code": 200 if success else 502, "body": response_payload}

        artifacts = [
            request_artifact,
            ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "marking_code_pool_export_response.json", response_payload),
            ArtifactCreate(ArtifactType.VALIDATION_RESULT.value, "marking_code_pool_export_actions.json", {"actions": actions, "warnings": response_payload["warnings"]}),
        ]
        if not success:
            return _failed(
                "MARKING_POOL_DELIVERY_INCOMPLETE",
                record.error_message or "CHZ marking code pool delivery failed",
                config,
                "Откройте actions artifact: там отдельно видны outbox, laser_file и external_forward.",
                artifacts,
            )
        return StepResult.success("CHZ marking code pool delivered", artifacts=artifacts, variables_update=variables)


class FlowReturnResponseStep:
    name = "flow_return_response"
    display_name = "Return Response"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        try:
            scope = _scope(context)
            if str(config.get("response_body_type") or "").lower() == "xml" and config.get("body_template") is not None:
                body = render_payload_xml_template(str(config.get("body_template") or ""), scope)
            elif config.get("body_template") is not None:
                body = render_template(str(config.get("body_template") or ""), scope)
            else:
                body = render_template(config.get("body") if config.get("body") is not None else "{{response}}", scope)
        except Exception as exc:
            return _failed("RETURN_RESPONSE_BUILD_FAILED", str(exc), config, "Check return body variable path.")
        body_type = str(config.get("response_body_type") or ("json" if isinstance(body, dict) else "raw_text"))
        if body_type == "xml" and isinstance(body, dict) and isinstance(body.get("xml"), str):
            body = body["xml"]
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


def _marking_code_pool_request(
    config: dict[str, Any],
    scope: dict[str, Any],
    context: PipelineContext,
) -> OneCMarkingCodePoolExportRequest:
    order_number = _required_text_from_path(scope, config.get("order_number_path"), "order_number_path")
    full_codes_base64 = _optional_list_from_path(scope, config.get("full_codes_base64_path"))
    codes = _optional_list_from_path(scope, config.get("codes_path"))
    source_document_id = _optional_text_from_path(scope, config.get("source_document_id_path"))
    source_document_name = _optional_text_from_path(scope, config.get("source_document_name_path"))

    # --- actions_override: supports {{template}} variables for dynamic control ---
    # Option 1: explicit actions_override dict (keys can use {{var}} templates)
    action_overrides_raw = config.get("actions_override")
    if isinstance(action_overrides_raw, dict):
        # Render each value so operators can write {"laser_file": "{{is_laser}}"}
        rendered = render_template(action_overrides_raw, scope)
        rendered_clean = {
            k: (None if v in (None, "") else _coerce_bool(v))
            for k, v in (rendered if isinstance(rendered, dict) else {}).items()
        }
        action_overrides = MarkingCodePoolActionOverrides(**rendered_clean)
    # Option 2: destination_path — operator points to request field with "laser"/"print"/"not_specified"
    # This auto-translates: laser/not_specified → laser_file=True; print → laser_file=False
    elif config.get("destination_path"):
        destination_raw = _optional_text_from_path(scope, config.get("destination_path")) or ""
        action_overrides = _destination_to_action_overrides(destination_raw)
    else:
        action_overrides = None

    metadata_json = config.get("metadata_json") if isinstance(config.get("metadata_json"), dict) else {}
    metadata_json = {
        **metadata_json,
        "flow_step_id": config.get("step_id"),
        "event_id": str(context.event.id),
        "run_id": str(context.run.id),
    }

    return OneCMarkingCodePoolExportRequest(
        source_system=str(config.get("source_system") or context.source_system or "1C ERP"),
        source_document_id=source_document_id,
        source_document_name=source_document_name,
        order_number=order_number,
        file_name=_optional_text_from_path(scope, config.get("file_name_path")) or config.get("file_name"),
        codes=codes,
        full_codes_base64=full_codes_base64,
        gs_marker=str(config.get("gs_marker") or "{GS}"),
        allow_overwrite=config.get("allow_overwrite"),
        actions_override=action_overrides,
        metadata_json=metadata_json,
    )


def _destination_to_action_overrides(destination: str) -> MarkingCodePoolActionOverrides:
    """Translate 1C/OMH destination string to laser_file on/off.

    Values:
      - "laser" or "not_specified" (or empty) → save laser file (laser_file=None → use global setting)
      - "print" → skip laser file (laser_file=False), still forward to DnP
    """
    value = destination.strip().lower()
    if value == "print":
        return MarkingCodePoolActionOverrides(laser_file=False)
    # "laser" and "not_specified" (and unknown/empty) → don't override, use global CHZ delivery settings
    return MarkingCodePoolActionOverrides()


def _coerce_bool(value: Any) -> bool | None:
    """Coerce a rendered template value to bool | None for actions_override fields."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value.lower() in {"true", "1", "yes"}:
            return True
        if value.lower() in {"false", "0", "no"}:
            return False
    return None


def _required_text_from_path(scope: dict[str, Any], path: Any, label: str) -> str:
    value = _optional_value_from_path(scope, path)
    if value in (None, ""):
        raise ValueError(f"{label} resolved to empty value")
    return str(value)


def _optional_text_from_path(scope: dict[str, Any], path: Any) -> str | None:
    value = _optional_value_from_path(scope, path)
    if value in (None, ""):
        return None
    return str(value)


def _optional_list_from_path(scope: dict[str, Any], path: Any) -> list[str] | None:
    value = _optional_value_from_path(scope, path)
    if value in (None, ""):
        return None
    if not isinstance(value, list):
        raise ValueError(f"{path} resolved to {type(value).__name__}, expected array")
    return [str(item) for item in value if str(item)]


def _optional_value_from_path(scope: dict[str, Any], path: Any) -> Any:
    if path in (None, ""):
        return None
    expression = str(path).strip()
    if not expression:
        return None
    try:
        return render_template(expression, scope) if "{{" in expression else resolve_path(scope, expression)
    except Exception:
        return None


def _marking_pool_request_summary(request: OneCMarkingCodePoolExportRequest) -> dict[str, Any]:
    override = request.actions_override.model_dump(mode="json") if request.actions_override else None
    return {
        "source_system": request.source_system,
        "source_document_id": request.source_document_id,
        "source_document_name": request.source_document_name,
        "order_number": request.order_number,
        "file_name": request.file_name,
        "codes_count": len(request.codes or []),
        "full_codes_base64_count": len(request.full_codes_base64 or []),
        "allow_overwrite": request.allow_overwrite,
        "actions_override": override,
        # Convenience: show resolved laser/forward flags so operator sees what will happen
        "effective_laser_file": override.get("laser_file") if override else None,
        "effective_external_forward": override.get("external_forward") if override else None,
    }


def _store_marking_pool_variables(variables: dict[str, Any], config: dict[str, Any], status: dict[str, Any]) -> None:
    save_as = str(config.get("save_as") or "marking_pool_export")
    variables[save_as] = status
    variables["marking_pool_export"] = status


def _selected_printer_name(config: dict[str, Any], scope: dict[str, Any]) -> tuple[str | None, str | None]:
    mode = str(config.get("mode") or "from_request")
    if mode == "rule_based":
        return None, "Выбор принтера по правилу будет добавлен позже."
    if mode == "fixed":
        return str(config.get("fixed_printer_name") or "").strip(), None
    try:
        return str(resolve_path(scope, str(config.get("path") or "request.body.printer")) or "").strip(), None
    except PathResolutionError:
        return None, "Принтер не найден в request.body.printer."


def _render_label_zpl(template: str, scope: dict[str, Any], item: dict[str, Any], labels: list[Any], item_as: str, index: int) -> str:
    label_scope = dict(scope)
    label_scope[item_as] = item
    label_scope["label"] = item
    label_scope["labels"] = {"items": labels, "length": len(labels)}
    label_scope["label_index"] = index
    return str(render_template(template, label_scope))


def _friendly_zpl_missing(path: str, labels_config: dict[str, Any]) -> str:
    item_as = str(labels_config.get("item_as") or "label")
    if path.startswith(f"{item_as}."):
        return f"В ZPL-шаблоне используется {path}, но такого поля нет в labels[0]."
    if path.startswith("label."):
        return f"В ZPL-шаблоне используется {path}, но такого поля нет в labels[0]."
    return f"В ZPL-шаблоне используется {path}, но такой переменной нет."


async def _find_print_target(context: PipelineContext, selected_printer: str) -> dict[str, Any] | None:
    from app.connectors.models import ConnectorInstance
    from app.printing.models import PrintPrinter

    printer_result = await context.session.execute(select(PrintPrinter).where(PrintPrinter.name == selected_printer))
    printer = printer_result.scalar_one_or_none()
    if printer is not None:
        return {"kind": "print_printer", "printer": printer}

    connector_result = await context.session.execute(select(ConnectorInstance).where(ConnectorInstance.name == selected_printer))
    connector = connector_result.scalar_one_or_none()
    if connector is not None and (connector.config_json or {}).get("training_mock_printer"):
        return {"kind": "training_mock", "connector": connector}

    training_result = await context.session.execute(select(ConnectorInstance).where(ConnectorInstance.name == "Training Printer"))
    training = training_result.scalar_one_or_none()
    if training is not None and (training.config_json or {}).get("training_mock_printer"):
        return {"kind": "training_mock", "connector": training}
    return None


def _job_key(scope: dict[str, Any], context: PipelineContext) -> str:
    try:
        value = resolve_path(scope, "request.body.job_key")
    except PathResolutionError:
        value = None
    return str(value or context.correlation_id or context.run.id)


def _sequence_no(item: dict[str, Any], index: int) -> int:
    value = item.get("sequence_no", index + 1)
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return index + 1
    return parsed if parsed > 0 else index + 1


def _normalized_print_status(print_job: dict[str, Any], selected_printer: str, labels: list[Any], *, dry_run: bool, printer_response: Any) -> dict[str, Any]:
    status = str(print_job.get("status") or ("dry_run" if dry_run else "sent"))
    if dry_run and status in {"sent", "printed"}:
        status = "dry_run"
    return {
        "success": True,
        "print_job_id": str(print_job.get("id") or ""),
        "labels_count": len(labels),
        "printer": selected_printer,
        "status": status,
        "dry_run": dry_run,
        "printer_response": printer_response,
    }


def _print_variables(
    context: PipelineContext,
    step_id: str,
    status: dict[str, Any],
    print_job: dict[str, Any],
    selected_printer: str,
    labels: list[Any],
    rendered: list[str],
    save_as: str,
    printer_response: Any,
) -> dict[str, Any]:
    variables = _variables_with_step(context, step_id, status)
    variables[save_as] = status
    variables["print_status"] = status
    variables["print_job"] = print_job
    variables["selected_printer"] = {"name": selected_printer}
    variables["labels"] = {"items": labels, "length": len(labels)}
    variables["rendered_zpl_labels"] = rendered
    variables["printer_response"] = printer_response
    return variables


def _config(context: PipelineContext) -> dict[str, Any]:
    return dict((context.current_step.step_config_json or {}).get("config") or {})


def _scope(context: PipelineContext) -> dict[str, Any]:
    payload = context.variables.get("payload") or {}
    return build_runtime_scope(request_body=payload, variables=context.variables, headers=payload.get("_headers") if isinstance(payload, dict) else {}, query=payload.get("_query") if isinstance(payload, dict) else {}, raw_text=payload.get("text") if isinstance(payload, dict) else None, xml=payload.get("xml") if isinstance(payload, dict) else None, context={"event_id": str(context.event.id), "run_id": str(context.run.id), "correlation_id": context.correlation_id})


def _variables_with_step(context: PipelineContext, step_id: str, value: Any) -> dict[str, Any]:
    steps = dict(context.variables.get("steps") or {})
    steps[step_id] = value
    return {"steps": steps}


async def _read_odata_items(context: PipelineContext, config: dict[str, Any], query: dict[str, Any], resource: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    connector_name = str(config.get("connection") or "")
    connector = await connector_repository.get_by_name(context.session, connector_name)
    if connector is None:
        raise ODataStepError("ODATA_CONNECTION_NOT_FOUND", f"OData connection {connector_name} not found", "Create or select a 1C connector with OData enabled.")
    if connector.connector_type != "onec":
        raise ODataStepError("ODATA_CONNECTION_NOT_FOUND", f"Connector {connector_name} is not a 1C/OData connector", "Select connector_type=onec.")
    connector_config = await SecretResolver(context.session).resolve_config(connector.config_json)
    mock_items = _mock_odata_items(config, connector_config, query, resource)
    if mock_items is not None:
        return mock_items, {"mock": True, "value": mock_items}
    if config.get("paginate") is False:
        connector_config = {**connector_config, "odata": {**(connector_config.get("odata") or {}), "max_pages": 1}}
    result = await read_odata(connector_config, resource, query)
    response_payload = result.response_payload or {"items_count": len(result.items)}
    if not result.success:
        raise ODataStepError(
            result.error_code or "ODATA_QUERY_FAILED",
            result.error_message or "OData query failed",
            "Check OData resource, filter, credentials and 1C availability.",
            response_payload,
        )
    return result.items, response_payload


def _saved_odata_value(items: list[dict[str, Any]], config: dict[str, Any]) -> Any:
    return items[0] if int(config.get("top") or 1) == 1 else items


def _collection(value: Any, scope: dict[str, Any]) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        expression = value.strip()
        if "{{" in expression:
            resolved = render_template(expression, scope)
        else:
            resolved = resolve_path(scope, expression)
        if isinstance(resolved, list):
            return resolved
        if resolved is None:
            return []
        raise ValueError(f"Foreach items resolved to {type(resolved).__name__}, expected array")
    raise ValueError("Foreach items must be an array or a path/template string")


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


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _mock_odata_items(config: dict[str, Any], connector_config: dict[str, Any], query: dict[str, Any], resource: str) -> list[dict[str, Any]] | None:
    if isinstance(config.get("mock_items"), list):
        return [item for item in config["mock_items"] if isinstance(item, dict)]
    mock_odata = (connector_config or {}).get("mock_odata") or {}
    if not isinstance(mock_odata, dict) or not mock_odata:
        return None
    response = query_mock_odata(mock_odata, resource or str(config.get("resource") or ""), query)
    items = response.get("value")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else None


def _training_target_response(connector_config: dict[str, Any], payload: dict[str, Any]) -> tuple[int, dict[str, Any]] | None:
    if connector_config.get("training_mock_dnp"):
        return submit_marking_pool(payload)
    if connector_config.get("training_mock_external_api"):
        return import_order(payload)
    if connector_config.get("training_mock_onec_shipment_facts") and _looks_like_shipment_fact(payload):
        return accept_shipment_fact(payload)
    if connector_config.get("training_mock_onec_writeback"):
        return save_order_external_id(payload)
    if connector_config.get("training_mock_site"):
        return import_order_to_site(payload)
    if connector_config.get("training_mock_printer"):
        return print_label(payload)
    return None


def _looks_like_shipment_fact(payload: dict[str, Any]) -> bool:
    body = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
    return isinstance(body, dict) and ("wms_shipment_id" in body or "warehouse_code" in body or "shipped_at" in body)


def _evaluate_condition(expression: str, scope: dict[str, Any]) -> bool:
    expression = expression.strip()
    match = re.fullmatch(r"(.+?)\s*(==|!=)\s*(.+)", expression) or re.fullmatch(r"(.+?)\s+(eq|ne)\s+(.+)", expression)
    if match:
        left_raw, operator, right_raw = match.groups()
        left = render_template(left_raw.strip(), scope) if left_raw.strip().startswith("{{") else resolve_path(scope, left_raw.strip())
        right = _condition_literal(right_raw.strip(), scope)
        return left != right if operator in {"!=", "ne"} else left == right
    if expression.endswith(" exists"):
        path = expression.removesuffix(" exists").strip()
        value = render_template(path, scope) if path.startswith("{{") else resolve_path(scope, path)
        return value not in (None, "", [], {})
    value = render_template(expression, scope)
    return bool(value)


def _endpoint_variables(context: PipelineContext, config: dict[str, Any], request_payload: dict[str, Any], response: dict[str, Any], response_body: Any) -> dict[str, Any]:
    variables = _variables_with_step(context, config["step_id"], {"request": request_payload, "response": response})
    variables["response"] = response
    save_as = str(config.get("save_response_as") or "").strip()
    if save_as:
        variables[save_as] = response_body
        variables[f"{save_as}_http"] = response
    return variables


def _endpoint_response_body(response: dict[str, Any]) -> Any:
    body = response.get("body")
    if isinstance(body, dict) and "body" in body and isinstance(body.get("body"), (dict, list, str, int, float, bool, type(None))):
        return body["body"]
    return body


def _response_artifact_names(body_type: str) -> tuple[str, str]:
    if body_type == "xml":
        return "response_template.xml", "rendered_response.xml"
    if body_type == "json":
        return "response_template.json", "rendered_response.json"
    return "response_template.txt", "rendered_response.txt"


def _condition_literal(value: str, scope: dict[str, Any]) -> Any:
    if value.startswith("{{"):
        return render_template(value, scope)
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.lower() in {"null", "none"}:
        return None
    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value


def _failed(code: str, message: str, config: dict[str, Any], hint: str, artifacts: list[ArtifactCreate] | None = None) -> StepResult:
    step_id = str(config.get("step_id") or "builder_step")
    return StepResult.failed(code, message, artifacts=artifacts or [ArtifactCreate(ArtifactType.ERROR_DETAILS.value, "builder_step_error.json", {"step_id": step_id, "error_code": code, "error_message": message, "hint": hint})], human_title=f"Builder step {step_id} failed", human_summary=message, developer_message=f"Step {step_id}: {message}", hint=hint)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {"value": value}


FOREACH_NESTED_TYPES = {"odata_query", "call_endpoint", "build_json", "extract"}

_FOREACH_NESTED_HANDLERS = {
    "call_endpoint": FlowCallEndpointStep,
    "build_json": FlowBuildJsonStep,
    "extract": FlowExtractStep,
}


async def _run_foreach_nested(
    nested_type: str,
    nested: dict[str, Any],
    context: PipelineContext,
    item_as: str,
    index_as: str,
    item: Any,
    index: int,
) -> tuple[Any, list[ArtifactCreate]]:
    nested_config = {key: value for key, value in nested.items() if key != "type"}
    nested_config["step_id"] = f"foreach_{index + 1}_{nested_type}"
    iteration_variables = dict(context.variables)
    iteration_variables[item_as] = item
    iteration_variables[index_as] = index
    iteration_variables["foreach"] = {"item": item, "index": index}
    fake_step = SimpleNamespace(id=None, step_config_json={"config": nested_config})
    sub_context = dataclasses.replace(context, current_step=fake_step, variables=iteration_variables)
    result = await _FOREACH_NESTED_HANDLERS[nested_type]().execute(sub_context)
    if result.status != StepResultStatus.SUCCESS:
        raise ValueError(result.error_message or result.message or f"nested {nested_type} step failed")
    save_key = str(nested.get("save_as") or nested.get("save_response_as") or "result")
    value = (result.variables_update or {}).get(save_key)
    artifacts = [
        ArtifactCreate(artifact.artifact_type, f"foreach_{index + 1}_{artifact.name}", artifact.content)
        for artifact in result.artifacts
    ]
    return value, artifacts


MAX_CALL_FLOW_DEPTH = 3


class FlowCallFlowStep:
    name = "flow_call_flow"
    display_name = "Call Flow"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        scope = _scope(context)
        flow_ref = str(config.get("flow") or "").strip()
        if not flow_ref:
            return _failed("SUBFLOW_NOT_SET", "Call flow step needs a flow slug or id", config, "Select a flow to reuse.")
        depth = int(context.metadata.get("call_flow_depth") or 0)
        if depth >= MAX_CALL_FLOW_DEPTH:
            return _failed("SUBFLOW_DEPTH_EXCEEDED", f"call_flow nesting is limited to {MAX_CALL_FLOW_DEPTH}", config, "Flatten the chain or reduce nesting.")
        flow = await _load_integration_flow(context.session, flow_ref)
        if flow is None:
            return _failed("SUBFLOW_NOT_FOUND", f"Flow {flow_ref} not found", config, "Check the flow slug in Integrations.")
        if not flow.enabled:
            return _failed("SUBFLOW_DISABLED", f"Flow {flow.slug} is disabled", config, "Enable the flow in Integrations.")
        if context.workflow is not None and flow.compiled_workflow_id == context.workflow.id:
            return _failed("SUBFLOW_SELF_CALL", "A flow cannot call itself", config, "Choose another flow.")
        try:
            mapped_input = _subflow_input(config, scope)
        except Exception as exc:
            return _failed("SUBFLOW_INPUT_BUILD_FAILED", str(exc), config, "Check the input mapping templates.")
        steps_json = await _subflow_steps(context.session, flow)
        if not steps_json:
            return _failed("SUBFLOW_NOT_COMPILED", f"Flow {flow.slug} has no compiled steps", config, "Open the flow and compile its workflow.")
        return await _execute_subflow(context, config, flow, steps_json, mapped_input, depth)


async def _load_integration_flow(session: Any, ref: str) -> Any:
    from app.integration_flows.models import IntegrationFlow

    try:
        from uuid import UUID as _UUID

        flow = await session.get(IntegrationFlow, _UUID(ref))
        if flow is not None:
            return flow
    except (ValueError, TypeError):
        pass
    result = await session.execute(select(IntegrationFlow).where(IntegrationFlow.slug == ref).limit(1))
    return result.scalar_one_or_none()


async def _subflow_steps(session: Any, flow: Any) -> list[dict[str, Any]]:
    if flow.builder_json:
        from app.flow_builder.compiler import FlowCompiler

        compiled = FlowCompiler().compile(flow.builder_json)
        if compiled["valid"]:
            return [step for step in compiled["steps_json"] if step.get("handler")]
    if flow.compiled_workflow_id:
        from app.workflows.models import Workflow

        workflow = await session.get(Workflow, flow.compiled_workflow_id)
        if workflow is not None:
            return [step for step in workflow.steps_json or [] if step.get("handler")]
    return []


def _subflow_input(config: dict[str, Any], scope: dict[str, Any]) -> Any:
    input_config = config.get("input")
    if isinstance(input_config, dict) and input_config:
        return build_json_from_template(input_config, scope)
    return (scope.get("request") or {}).get("body") or {}


async def _execute_subflow(
    context: PipelineContext,
    config: dict[str, Any],
    flow: Any,
    steps_json: list[dict[str, Any]],
    mapped_input: Any,
    depth: int,
) -> StepResult:
    from app.execution.registry import registry as step_registry

    sub_variables = dict(context.variables)
    sub_variables["payload"] = mapped_input
    sub_context = dataclasses.replace(context, variables=sub_variables, metadata={**context.metadata, "call_flow_depth": depth + 1})
    artifacts: list[ArtifactCreate] = []
    executed: list[str] = []
    for step_config in steps_json:
        step_name = str(step_config.get("name") or "step")
        if step_name in set(sub_context.variables.get("skip_steps") or []):
            continue
        if str(step_config.get("on") or "always") not in {"always", "on_success", "on_dry_run"}:
            continue
        run_if = (step_config.get("config") or {}).get("run_if")
        if run_if and not evaluate_matcher_group(run_if, _matcher_context_from_scope(_scope(sub_context)))["matched"]:
            continue
        handler_name = str(step_config.get("handler") or step_name)
        try:
            step_handler = step_registry.get(handler_name)
        except Exception:
            return _failed("SUBFLOW_STEP_UNKNOWN", f"Sub-flow {flow.slug} uses unknown step handler {handler_name}", config, "Compile the nested flow with the current OMH version.", artifacts)
        fake_step = SimpleNamespace(id=None, step_config_json=step_config)
        iteration_context = dataclasses.replace(sub_context, current_step=fake_step)
        result = await step_handler.execute(iteration_context)
        artifacts.extend(
            ArtifactCreate(artifact.artifact_type, f"subflow_{flow.slug}/{artifact.name}", artifact.content)
            for artifact in result.artifacts
        )
        if result.status != StepResultStatus.SUCCESS:
            error = result.error_message or result.message or "subflow step failed"
            artifacts.append(ArtifactCreate(ArtifactType.ERROR_DETAILS.value, f"subflow_{flow.slug}/error.json", {"step": step_name, "error_code": result.error_code, "error": error}))
            return _failed("SUBFLOW_STEP_FAILED", f"Sub-flow {flow.slug} failed at step {step_name}: {error}", config, "Open subflow artifacts and fix the nested flow first.", artifacts)
        executed.append(step_name)
        sub_context.variables.update(result.variables_update)
    save_as = str(config.get("save_as") or config["step_id"])
    output = {key: value for key, value in sub_context.variables.items() if key not in {"payload", "steps", "skip_steps"} and not str(key).startswith("_")}
    variables = _variables_with_step(context, config["step_id"], {"flow": flow.slug, "executed_steps": executed, "output": output})
    variables[save_as] = output
    artifacts.append(ArtifactCreate(ArtifactType.CANONICAL_PAYLOAD.value, f"subflow_{flow.slug}/output.json", {"flow": flow.slug, "executed_steps": executed, "output": output}))
    return StepResult.success(f"Sub-flow {flow.slug} complete", artifacts=artifacts, variables_update=variables)


OZON_ACTIONS = {"list_products", "product_info", "get_stocks", "update_stocks", "get_prices", "update_prices", "list_orders", "list_warehouses"}

OZON_MOCK_RESPONSES: dict[str, Any] = {
    "list_products": {"result": {"items": [{"product_id": 1234567, "offer_id": "ABC-123", "has_fbo_stocks": False, "has_fbs_stocks": True, "archived": False, "is_discounted": False}], "last_id": "WzE=", "total": 1}},
    "product_info": {"result": {"items": [{"id": 1234567, "name": "Тестовый товар", "offer_id": "ABC-123", "barcode": "4600000000001", "sku": 12345678}]}},
    "get_stocks": {"cursor": "", "total": 1, "items": [{"offer_id": "ABC-123", "product_id": 1234567, "stocks": [{"present": 15, "reserved": 2, "sku": 12345678}]}]},
    "update_stocks": {"result": [{"offer_id": "ABC-123", "product_id": 1234567, "updated": True, "errors": []}]},
    "get_prices": {"items": [{"id": 1234567, "price": {"price": "100.00", "old_price": "120.00", "premium_price": "90.00", "min_price": "80.00", "currency": "RUB"}}], "cursor": "", "total": 1},
    "update_prices": {"result": [{"product_id": 1234567, "offer_id": "ABC-123", "updated": True, "errors": []}]},
    "list_orders": {"result": {"postings": [{"posting_number": "00000001-0001-1", "order_id": 50001, "order_number": "00000001-0001", "status": "awaiting_packaging", "created_at": "2026-08-06T10:00:00Z", "products": [{"sku": 12345678, "offer_id": "ABC-123", "name": "Тестовый товар", "quantity": 1, "price": "100.00"}], "analytics_data": {"city": "Москва", "region": "Московская область"}}], "count": 1}},
    "list_warehouses": {"result": [{"warehouse_id": 1001, "name": "Основной склад"}]},
}


class FlowOzonActionStep:
    name = "flow_ozon_action"
    display_name = "Ozon Action"

    async def execute(self, context: PipelineContext) -> StepResult:
        config = _config(context)
        scope = _scope(context)
        action = str(config.get("action") or "").strip()
        if action not in OZON_ACTIONS:
            return _failed("OZON_ACTION_INVALID", f"Unsupported ozon action: {action or '(not set)'}", config, f"Choose one of: {', '.join(sorted(OZON_ACTIONS))}.")
        save_as = str(config.get("save_as") or config["step_id"])
        summary_config = {
            "action": action,
            "connector": config.get("connector"),
            "offer_ids": _ozon_list_param(config, scope, "offer_ids", "offer_ids_path"),
            "product_ids": _ozon_list_param(config, scope, "product_ids", "product_ids_path"),
            "stocks": _ozon_list_param(config, scope, "stocks", "stocks_path"),
            "prices": _ozon_list_param(config, scope, "prices", "prices_path"),
            "since": _ozon_text_param(config, scope, "since"),
            "status": _ozon_text_param(config, scope, "status"),
            "limit": config.get("limit"),
        }
        request_artifact = ArtifactCreate(ArtifactType.OUTGOING_REQUEST.value, "ozon_request.json", summary_config)
        mock = config.get("mock_json") if isinstance(config.get("mock_json"), (dict, list)) else None
        if mock is None and isinstance(config.get("mock_response_json"), (dict, list)):
            mock = config["mock_response_json"]
        if context.dry_run or mock is not None:
            response = mock if mock is not None else OZON_MOCK_RESPONSES[action]
            return _ozon_success(context, config, action, save_as, response, [request_artifact], mock=True)

        try:
            client = await _ozon_client_from_config(context, config)
        except Exception as exc:
            return _failed("OZON_CONFIG_INVALID", str(exc), config, "Fill client_id/api_key in the Ozon connector (secret reference supported).", [request_artifact])
        try:
            response = await _ozon_execute(client, action, summary_config)
        except Exception as exc:
            return _failed("OZON_API_FAILED", str(exc), config, "Check Ozon key role, rate limits and Ozon availability.", [request_artifact])

        errors = _ozon_item_errors(action, response)
        response_artifact = ArtifactCreate(ArtifactType.INCOMING_RESPONSE.value, "ozon_response.json", _ozon_response_summary(action, response))
        if errors:
            return _failed(
                "OZON_ITEMS_FAILED",
                f"Ozon обновил не все позиции: {len(errors)} ошибок. Первая: {errors[0]}",
                config,
                "Откройте ozon_response.json: в errors указано, какие offer_id не принял Ozon и почему.",
                [request_artifact, response_artifact],
            )
        return _ozon_success(context, config, action, save_as, response, [request_artifact, response_artifact])


def _ozon_success(context: PipelineContext, config: dict[str, Any], action: str, save_as: str, response: Any, artifacts: list[ArtifactCreate], *, mock: bool = False) -> StepResult:
    result = _ozon_canonical(action, response)
    if mock:
        result = {**result, "mock": True} if isinstance(result, dict) else result
    variables = _variables_with_step(context, config["step_id"], {"action": action, "result": result})
    variables[save_as] = result
    return StepResult.success(f"Ozon {action} complete" + (" (mock)" if mock else ""), artifacts=artifacts, variables_update=variables)


def _ozon_canonical(action: str, response: Any) -> Any:
    if action in {"update_stocks", "update_prices"}:
        result = (response or {}).get("result") or []
        return {
            "updated": [item for item in result if item.get("updated")],
            "errors": [{"offer_id": item.get("offer_id") or item.get("product_id"), "errors": item.get("errors") or []} for item in result if item.get("errors")],
        }
    if action == "list_orders":
        result = (response or {}).get("result") or {}
        postings = result.get("postings") or []
        return {
            "count": result.get("count", len(postings)),
            "orders": [_ozon_canonical_order(posting) for posting in postings],
        }
    if action == "list_products":
        result = (response or {}).get("result") or {}
        return {"items": result.get("items") or [], "last_id": result.get("last_id") or "", "total": result.get("total", 0)}
    if action == "get_stocks":
        return {"items": (response or {}).get("items") or [], "cursor": (response or {}).get("cursor") or "", "total": (response or {}).get("total", 0)}
    if action == "get_prices":
        return {"items": (response or {}).get("items") or [], "cursor": (response or {}).get("cursor") or "", "total": (response or {}).get("total", 0)}
    return response


def _ozon_canonical_order(posting: dict[str, Any]) -> dict[str, Any]:
    analytics = posting.get("analytics_data") or {}
    return {
        "marketplace": "ozon",
        "posting_number": posting.get("posting_number"),
        "order_number": posting.get("order_number"),
        "status": posting.get("status"),
        "created_at": posting.get("created_at"),
        "customer_region": analytics.get("region") or analytics.get("city"),
        "items": [
            {
                "offer_id": product.get("offer_id"),
                "sku": product.get("sku"),
                "name": product.get("name"),
                "qty": product.get("quantity"),
                "price": product.get("price"),
            }
            for product in posting.get("products") or []
        ],
    }


def _ozon_item_errors(action: str, response: Any) -> list[str]:
    if action not in {"update_stocks", "update_prices"}:
        return []
    errors: list[str] = []
    for item in (response or {}).get("result") or []:
        for error in item.get("errors") or []:
            errors.append(f"{item.get('offer_id') or item.get('product_id')}: {error.get('description') or error.get('code')}")
    return errors


def _ozon_response_summary(action: str, response: Any) -> Any:
    canonical = _ozon_canonical(action, response)
    if isinstance(canonical, dict):
        summary = dict(canonical)
        for key in ("items", "orders"):
            value = summary.get(key)
            if isinstance(value, list) and len(value) > 50:
                summary[key] = value[:50]
                summary[f"{key}_truncated"] = True
        return summary
    return {"response": canonical}


def _ozon_list_param(config: dict[str, Any], scope: dict[str, Any], key: str, path_key: str) -> list[Any] | None:
    value = config.get(key)
    if isinstance(value, list) and value:
        return value
    path = str(config.get(path_key) or "").strip()
    if not path:
        return None
    resolved = resolve_path(scope, path)
    if isinstance(resolved, list):
        return resolved
    return None


def _ozon_text_param(config: dict[str, Any], scope: dict[str, Any], key: str) -> str | None:
    value = config.get(key)
    if value is None:
        return None
    try:
        text = str(render_template(str(value), scope) or "").strip()
    except Exception:
        return None
    return text or None


async def _ozon_client_from_config(context: PipelineContext, config: dict[str, Any]) -> Any:
    from app.ozon.client import OzonClient

    connector_name = str(config.get("connector") or "").strip()
    if not connector_name:
        raise ValueError("Укажите Ozon connector в шаге (Connection Profile с client_id/api_key).")
    connector = await connector_repository.get_by_name(context.session, connector_name)
    if connector is None:
        raise ValueError(f"Ozon connector {connector_name} не найден. Создайте его в Connection Center.")
    connector_config = await SecretResolver(context.session).resolve_config(connector.config_json)
    return OzonClient(
        client_id=str(connector_config.get("client_id") or ""),
        api_key=str(connector_config.get("api_key") or ""),
        base_url=str(connector_config.get("base_url") or connector_config.get("url") or "") or "https://api-seller.ozon.ru",
        timeout_seconds=float(connector_config.get("timeout_seconds") or 30),
    )


async def _ozon_execute(client: Any, action: str, params: dict[str, Any]) -> Any:
    limit = int(params.get("limit") or 1000)
    if action == "list_products":
        return await client.list_products(limit=limit)
    if action == "product_info":
        return await client.product_info_list(offer_ids=params.get("offer_ids"), product_ids=params.get("product_ids"))
    if action == "get_stocks":
        return await client.get_stocks(offer_ids=params.get("offer_ids"), product_ids=params.get("product_ids"), limit=limit)
    if action == "update_stocks":
        stocks = params.get("stocks") or []
        return await client.update_stocks([_ozon_stock_row(row) for row in stocks])
    if action == "get_prices":
        return await client.get_prices(offer_ids=params.get("offer_ids"), product_ids=params.get("product_ids"), limit=limit)
    if action == "update_prices":
        prices = params.get("prices") or []
        return await client.update_prices([_ozon_price_row(row) for row in prices])
    if action == "list_orders":
        since = params.get("since")
        if not since:
            raise ValueError("Для list_orders укажите since (дата ISO, например {{variables.last_sync}} или 2026-08-01T00:00:00Z).")
        return await client.list_fbs_orders(since=since, status=params.get("status"), limit=min(limit, 100))
    if action == "list_warehouses":
        return await client.list_warehouses()
    raise ValueError(f"Unsupported ozon action: {action}")


def _ozon_stock_row(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"offer_id": str(row), "stock": 0}
    result: dict[str, Any] = {}
    if row.get("offer_id"):
        result["offer_id"] = row["offer_id"]
    if row.get("product_id"):
        result["product_id"] = row["product_id"]
    result["stock"] = int(row.get("stock", row.get("qty", row.get("quantity", 0))))
    return result


def _ozon_price_row(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {"offer_id": str(row), "price": "0"}
    result: dict[str, Any] = {}
    if row.get("offer_id"):
        result["offer_id"] = row["offer_id"]
    if row.get("product_id"):
        result["product_id"] = row["product_id"]
    for source, target in (("price", "price"), ("old_price", "old_price"), ("premium_price", "premium_price"), ("min_price", "min_price")):
        if row.get(source) is not None:
            result[target] = str(row[source])
    result["currency"] = str(row.get("currency") or "RUB")
    return result
