from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select

from app.connectors import repository as connector_repository
from app.connectors.builtin.onec.odata import read_odata
from app.connectors.builtin.rest_connector import RESTConnector
from app.connectors.manager import ConnectorManager
from app.core.enums import ArtifactType
from app.execution.context import PipelineContext
from app.execution.result import ArtifactCreate, StepResult
from app.integration_master.payload_renderer import PayloadRenderError, render_payload_step, render_xml_template as render_payload_xml_template
from app.integration_master.schemas import PayloadStepConfig
from app.json_builder.engine import build_json_from_fields, build_json_from_template
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
        if not isinstance(nested, dict) or nested.get("type") != "odata_query":
            return _failed("FOREACH_STEP_UNSUPPORTED", "Foreach currently supports nested odata_query", config, "Set step.type to odata_query.")

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
        try:
            ok = _evaluate_condition(str(config.get("if") or ""), _scope(context))
        except Exception as exc:
            return _failed(
                "CONDITION_EVALUATION_FAILED",
                str(exc),
                config,
                "Check previous step variables and condition path.",
            )
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
        connector_context = ConnectorContext(event_id=context.event.id, run_id=context.run.id, step_id=context.current_step.id if context.current_step else None, correlation_id=context.correlation_id, source_system=context.source_system, target_system=connector_name, dry_run=context.dry_run, metadata={"step_name": config["step_id"], "path": config.get("path"), "method": request_payload["method"]})
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
    match = re.fullmatch(r"(.+?)\s*(==|!=|eq|ne)\s*(.+)", expression)
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
    if isinstance(body, dict) and isinstance(body.get("body"), (dict, list, str, int, float, bool, type(None))):
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
