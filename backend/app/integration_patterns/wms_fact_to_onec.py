from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import IntegrationFlowSourceType, IntegrationFlowTargetType
from app.core.errors import BadRequestError, NotFoundError
from app.flow_builder.validator import validate_builder
from app.integration_flows import service as integration_flows_service
from app.integration_flows.models import IntegrationFlow
from app.integration_flows.schemas import EndpointBuilderConfig, IntegrationFlowCreate
from app.integration_master import service as master_service
from app.integration_master.payload_renderer import PayloadRenderError, render_json_template, resolve_template_path
from app.integration_master.schemas import (
    CompileDraftResponse,
    CompiledRunTestRequest,
    InputContract,
    InputParseRequest,
    ODataStepConfig,
    ODataStepRequest,
    ODataStepTestResponse,
    PayloadStepConfig,
    PayloadStepRequest,
)
from app.integration_patterns.schemas import (
    WmsFactToOneCCallerResponseConfig,
    WmsFactToOneCCreateResponse,
    WmsFactToOneCODataLookupConfig,
    WmsFactToOneCPatternRequest,
    WmsFactToOneCPreviewResponse,
    WmsFactToOneCRunTestRequest,
    WmsFactToOneCRunTestResponse,
    WmsFactToOneCServiceConfig,
)
from app.odata_connections import service as odata_connections_service
from app.test_console.models import SavedTestCase
from app.integration_patterns._common import (
    ensure_slug_available as _ensure_slug_available,
    dedupe as _dedupe,
)


ONEC_SHIPMENT_SUCCESS_RESPONSE = {
    "success": True,
    "external_document_id": "1C-SHIP-WMS-SHIP-123",
    "status": "accepted",
    "message": "Shipment fact accepted",
}


async def preview_pattern(session: AsyncSession, request: WmsFactToOneCPatternRequest) -> WmsFactToOneCPreviewResponse:
    contract = _contract(request)
    lookup = request.odata_lookup
    payload_step = _payload_step(request.onec_payload)
    service = request.onec_http_service

    input_validation = master_service.validate_input_contract(contract)
    request_shape_errors = _validate_wms_sample(contract)
    base_variables = _base_variables(contract)
    lookup_variables = dict(base_variables)
    odata_request: dict[str, Any] = {"enabled": lookup.enabled}
    odata_result: dict[str, Any] | None = None
    lookup_errors: list[str] = []
    lookup_warnings: list[str] = []
    odata_preview = None
    odata_test: ODataStepTestResponse | None = None

    if lookup.enabled:
        odata_step = lookup.config
        odata_preview = master_service.preview_odata_step(ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=odata_step))
        odata_test = await master_service.test_odata_step(session, ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=odata_step))
        odata_result = odata_test.result_preview if odata_test.success else None
        lookup_variables[odata_step.save_as.strip() or "order"] = odata_result or _sample_odata_object(odata_step.select)
        lookup_errors.extend([] if odata_preview.valid else odata_preview.errors)
        if not odata_test.success:
            lookup_errors.append(_friendly_odata_error(contract, odata_test))
        lookup_warnings.extend(odata_preview.warnings)
        odata_request = {
            "enabled": True,
            "resource": odata_preview.rendered_resource,
            "template_filter": odata_preview.template_filter,
            "rendered_filter": odata_preview.rendered_filter,
            "template_url": odata_preview.template_url,
            "rendered_url": odata_preview.rendered_url,
            "request": odata_test.request,
            "save_as": odata_preview.saved_as,
        }
    else:
        order_save_as = lookup.config.save_as.strip() or "order"
        order_required = _template_uses_variable(payload_step.template, order_save_as)
        order_ref_key, disabled_errors = _disabled_order_ref(lookup, base_variables) if order_required else (None, [])
        lookup_errors.extend(disabled_errors)
        lookup_variables[order_save_as] = {
            "Ref_Key": order_ref_key or "",
            "Number": _business_value(contract, "request.body.order_number") or "",
        }
        odata_request = {"enabled": False, "order_ref_key_path": lookup.order_ref_key_path, "save_as": order_save_as, "order_ref_key_required": order_required}

    payload_preview = master_service.preview_payload_step(PayloadStepRequest(input_contract=contract, previous_variables=lookup_variables, payload_step=payload_step))
    variables_after_payload = dict(lookup_variables)
    if payload_preview.valid:
        variables_after_payload[payload_step.save_as] = payload_preview.rendered_body

    onec_request, onec_request_errors = _onec_service_preview(service, variables_after_payload, default_body_source=payload_step.save_as)
    onec_response = _onec_response_sample(service)
    variables_after_onec = dict(variables_after_payload)
    variables_after_onec[service.save_response_as.strip() or "onec_response"] = onec_response

    response_to_caller, caller_errors = _caller_response_preview(request.caller_response, variables_after_onec, onec_response_as=service.save_response_as.strip() or "onec_response")
    builder_json = await _builder_json(session, request, contract, odata_request.get("template_filter") if lookup.enabled else None)
    builder_validation = validate_builder(builder_json)

    errors = _dedupe(
        [
            *input_validation.get("errors", []),
            *request_shape_errors,
            *lookup_errors,
            *_friendly_payload_errors(payload_preview.errors, [lookup.config.save_as]),
            *onec_request_errors,
            *caller_errors,
            *[str(item.get("message") or item.get("code")) for item in builder_validation.get("errors", [])],
        ]
    )
    warnings = _dedupe(
        [
            *lookup_warnings,
            *payload_preview.warnings,
            *_onec_business_warnings(onec_response),
            *[str(item.get("message") or item.get("code")) for item in builder_validation.get("warnings", [])],
        ]
    )

    return WmsFactToOneCPreviewResponse(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        endpoint={"method": "POST", "url": master_service.endpoint_url(contract.slug)},
        incoming_request=contract.sample,
        odata_request=odata_request,
        odata_result=odata_result,
        onec_payload=payload_preview.rendered_body if payload_preview.valid else None,
        onec_request=onec_request,
        onec_response=onec_response,
        response_to_caller=response_to_caller,
        human_steps=[
            f"Получен складской факт от WMS: {_operation_label(contract)}",
            "Найден заказ в 1С" if lookup.enabled else "OData lookup заказа пропущен",
            "Собран payload для 1С",
            "Отправлено в 1С HTTP service",
            "Ответ 1С возвращён WMS",
        ],
        advanced={
            "input_contract_validation": input_validation,
            "request_shape_errors": request_shape_errors,
            "odata_lookup": lookup.model_dump(mode="json"),
            "odata_preview": odata_preview.model_dump(mode="json") if odata_preview else None,
            "odata_test": odata_test.model_dump(mode="json") if odata_test else None,
            "payload_step": payload_step.model_dump(mode="json"),
            "payload_preview": payload_preview.model_dump(mode="json"),
            "onec_http_service": service.model_dump(mode="json"),
            "caller_response": request.caller_response.model_dump(mode="json"),
            "builder_json": builder_json,
            "builder_validation": builder_validation,
            "variables_after_lookup": lookup_variables,
            "variables_after_payload": variables_after_payload,
            "variables_after_onec": variables_after_onec,
        },
    )


async def create_pattern(session: AsyncSession, request: WmsFactToOneCPatternRequest) -> WmsFactToOneCCreateResponse:
    contract = _contract(request)
    await _ensure_slug_available(session, contract.slug)
    preview = await preview_pattern(session, request)
    if not preview.valid:
        raise BadRequestError("; ".join(preview.errors))

    parse_result = master_service.parse_contract_input(InputParseRequest(input_mode=contract.input_mode, sample=contract.sample, scenario_key=contract.scenario_key))
    draft = await master_service.save_draft(session, contract, parse_result)
    builder_json = preview.advanced.get("builder_json")
    if not isinstance(builder_json, dict):
        raise BadRequestError("Preview не вернул builder_json для сохранения. Повторите preview и create.")
    flow_payload = _flow_payload(contract, builder_json, request.onec_http_service, enabled=False)
    flow = await integration_flows_service.create_flow(session, flow_payload)
    test_case = await _test_case_for_flow(session, flow)
    if flow.endpoint_id is None or flow.route_id is None:
        raise BadRequestError("Compiled integration was created without endpoint or route. Transaction rolled back.")
    return WmsFactToOneCCreateResponse(draft_id=draft.id, compile=_compile_response(flow, test_case), preview=preview)


async def run_test(session: AsyncSession, request: WmsFactToOneCRunTestRequest) -> WmsFactToOneCRunTestResponse:
    result = await master_service.run_compiled_test(session, request.integration_flow_id, CompiledRunTestRequest(dry_run=request.dry_run))
    return WmsFactToOneCRunTestResponse(**result.model_dump())


def _contract(request: WmsFactToOneCPatternRequest) -> InputContract:
    contract = request.input_contract
    return contract.model_copy(
        update={
            "name": request.name.strip(),
            "slug": request.slug.strip(),
            "scenario_key": contract.scenario_key or "wms_shipment_fact",
            "source_system": contract.source_system or "wms",
            "endpoint_url": master_service.endpoint_url(request.slug.strip()),
        }
    )


def _payload_step(payload: PayloadStepConfig) -> PayloadStepConfig:
    save_as = (payload.save_as or "onec_payload").strip() or "onec_payload"
    return payload.model_copy(update={"save_as": save_as, "overwrite": True})


async def _builder_json(session: AsyncSession, request: WmsFactToOneCPatternRequest, contract: InputContract, odata_filter: str | None) -> dict[str, Any]:
    lookup = request.odata_lookup
    payload = _payload_step(request.onec_payload)
    steps: list[dict[str, Any]] = []
    if lookup.enabled:
        odata_step = await _with_connection_name(session, lookup.config)
        steps.append(
            {
                "id": "find_order",
                "type": "odata_query",
                "name": "Найден заказ в 1С",
                "connection": odata_step.connection_name or str(odata_step.connection_id or ""),
                "resource": odata_step.resource,
                "filter": odata_filter or odata_step.filter,
                "select": odata_step.select,
                "top": odata_step.top,
                "orderby": odata_step.orderby,
                "paginate": odata_step.paginate,
                "save_as": odata_step.save_as,
                "required": odata_step.required,
            }
        )
    else:
        save_as = lookup.config.save_as.strip() or "order"
        if _template_uses_variable(payload.template, save_as):
            steps.append(
                {
                    "id": "map_order_ref_key",
                    "type": "build_payload",
                    "name": "Ref_Key заказа получен из WMS",
                    "body_type": "json",
                    "save_as": save_as,
                    "json_mode": "raw_template",
                    "template": {
                        "Ref_Key": "{{" + lookup.order_ref_key_path.strip() + "}}",
                        "Number": "{{request.body.order_number}}",
                    },
                    "fields": [],
                    "dynamic_entries": [],
                }
            )
    steps.extend(
        [
            _payload_builder_step("build_onec_payload", "Собран payload для 1С", payload),
            _call_onec_step("send_onec_http_service", "Отправлено в 1С HTTP service", request.onec_http_service, body_source=payload.save_as),
            _return_response_step(request.caller_response, onec_response_as=request.onec_http_service.save_response_as.strip() or "onec_response"),
        ]
    )
    return {
        "version": 1,
        "source": {
            "generated_by": "wms_fact_to_onec_pattern",
            "pattern_id": "wms_fact_to_onec",
            "input_mode": contract.input_mode,
            "sample": contract.sample,
            "operation_key": contract.operation_key.model_dump(mode="json"),
            "business_key": contract.business_key.model_dump(mode="json"),
        },
        "steps": steps,
    }


def _payload_builder_step(step_id: str, name: str, payload: PayloadStepConfig) -> dict[str, Any]:
    return {
        "id": step_id,
        "type": "build_payload",
        "name": name,
        "body_type": payload.body_type,
        "save_as": payload.save_as,
        "json_mode": payload.json_mode,
        "template": payload.template,
        "fields": [field.model_dump(mode="json") for field in payload.fields],
        "dynamic_entries": [entry.model_dump(mode="json") for entry in payload.dynamic_entries],
    }


def _call_onec_step(step_id: str, name: str, service: WmsFactToOneCServiceConfig, *, body_source: str) -> dict[str, Any]:
    connector_name = (service.connector_name or "").strip()
    direct_url = service.url.strip() if service.url.strip() else "" if connector_name else _onec_url(service)
    return {
        "id": step_id,
        "type": "call_endpoint",
        "name": name,
        "method": service.method,
        "connector": connector_name or None,
        "operation": service.operation,
        "url": direct_url,
        "path": service.path,
        "headers": service.headers,
        "body": _body_template(service.body_source or body_source),
        "body_type": service.body_type,
        "timeout_seconds": service.timeout_seconds,
        "save_response_as": service.save_response_as,
        "mock_response_json": service.mock_response_json if service.mock_response_json is not None else ONEC_SHIPMENT_SUCCESS_RESPONSE,
    }


def _return_response_step(response: WmsFactToOneCCallerResponseConfig, *, onec_response_as: str) -> dict[str, Any]:
    if response.type == "accepted_event":
        body: Any = {"accepted": True, "event_id": "{{context.event_id}}", "run_id": "{{context.run_id}}"}
        status_code = 202
    elif response.type == "raw_onec_response":
        body = "{{" + onec_response_as + "}}"
        status_code = response.status_code
    else:
        body = response.body
        status_code = response.status_code
    return {"id": "return_response", "type": "return_response", "name": "Ответ 1С возвращён WMS", "status_code": status_code, "body": body, "headers": response.headers, "response_body_type": "json"}


def _body_template(body_source: str) -> str:
    if body_source == "none":
        return ""
    return "{{" + body_source + "}}"


def _onec_service_preview(service: WmsFactToOneCServiceConfig, variables: dict[str, Any], *, default_body_source: str) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    connector_name = (service.connector_name or "").strip()
    direct_url = service.url.strip() if service.url.strip() else "" if connector_name else _onec_url(service)
    if not connector_name and not _valid_http_url(direct_url):
        errors.append("URL 1С HTTP service должен начинаться с http:// или https://, если connector не выбран.")
    if connector_name and not (service.path or "").strip():
        errors.append("Для 1С HTTP service connector укажите Path, например /shipment-facts.")
    if not (service.save_response_as or "").strip():
        errors.append("Укажите Save response as для ответа 1С, например onec_response.")
    body, body_errors = _render_body(service.body_source or default_body_source, variables)
    errors.extend(body_errors)
    if errors:
        return None, errors
    return (
        {
            "method": service.method,
            "connector": connector_name or None,
            "operation": service.operation,
            "url": direct_url or None,
            "path": service.path,
            "headers": render_json_template(service.headers, variables),
            "body_type": service.body_type,
            "body_preview": body,
            "timeout_seconds": service.timeout_seconds,
            "save_response_as": service.save_response_as,
        },
        [],
    )


def _render_body(body_source: str, variables: dict[str, Any]) -> tuple[Any, list[str]]:
    try:
        if body_source == "none":
            return None, []
        return resolve_template_path(body_source, variables), []
    except PayloadRenderError as exc:
        return None, [str(exc)]


def _caller_response_preview(response: WmsFactToOneCCallerResponseConfig, variables: dict[str, Any], *, onec_response_as: str) -> tuple[Any, list[str]]:
    try:
        if response.type == "accepted_event":
            context = variables.get("context") if isinstance(variables.get("context"), dict) else {}
            return {"accepted": True, "event_id": context.get("event_id"), "run_id": context.get("run_id")}, []
        if response.type == "raw_onec_response":
            return resolve_template_path(onec_response_as, variables), []
        return render_json_template(response.body, variables), []
    except PayloadRenderError as exc:
        return None, [str(exc)]


def _onec_response_sample(service: WmsFactToOneCServiceConfig) -> dict[str, Any]:
    return service.mock_response_json if isinstance(service.mock_response_json, dict) else ONEC_SHIPMENT_SUCCESS_RESPONSE


def _onec_business_warnings(response: Any) -> list[str]:
    if not isinstance(response, dict) or response.get("success") is not False:
        return []
    message = response.get("error_message") or response.get("message") or "1С вернула бизнес-ошибку."
    return [f"1С вернула бизнес-ошибку: {message}"]


def _onec_url(service: WmsFactToOneCServiceConfig) -> str:
    if (service.url or "").strip():
        return service.url.strip()
    base = (service.base_url or "").strip().rstrip("/") + "/"
    path = (service.path or "").strip().lstrip("/")
    return urljoin(base, path)


def _valid_http_url(url: str) -> bool:
    return bool(re.match(r"^https?://[^\s]+", url or ""))


async def _with_connection_name(session: AsyncSession, step: ODataStepConfig) -> ODataStepConfig:
    if step.connection_name or not step.connection_id:
        return step
    try:
        connection = await odata_connections_service.get_connection(session, step.connection_id)
        return step.model_copy(update={"connection_name": connection.name})
    except NotFoundError:
        return step


def _flow_payload(contract: InputContract, builder_json: dict[str, Any], service: WmsFactToOneCServiceConfig, *, enabled: bool) -> IntegrationFlowCreate:
    slug = contract.slug
    writeback_step = _builder_step(builder_json, "send_onec_http_service")
    action_json = {
        "type": "call_1c_http_service",
        "operation": service.operation or "update_shipment_status",
        "business_object": slug,
        "method": writeback_step.get("method") or "POST",
        "url": writeback_step.get("url"),
        "path": writeback_step.get("path"),
        "target_connector": writeback_step.get("connector"),
        "body_mode": writeback_step.get("body_type") or "json",
        "response_mode": "sync_response",
        "comment": "Created from WMS/API -> OMH -> 1C HTTP service pattern wizard",
    }
    return IntegrationFlowCreate(
        name=f"{contract.name} [{slug}]",
        slug=slug,
        description="Created from WMS/API -> OMH -> 1C HTTP service pattern wizard.",
        enabled=enabled,
        source_type=_source_type(contract.source_system),
        target_type=IntegrationFlowTargetType.ONEC,
        endpoint=EndpointBuilderConfig(input_mode=contract.input_mode, response_mode="sync_response", auth_mode="none", auth_config_json={}),
        matcher_group_json=_matcher_group(contract),
        action_json=action_json,
        response_config_json={
            "response_mode": "sync_response",
            "pattern_id": "wms_fact_to_onec",
            "business_key": contract.business_key.model_dump(mode="json"),
            "onec_response_as": writeback_step.get("save_response_as"),
        },
        builder_json=builder_json,
        test_payload_json=_test_payload_json(contract),
        test_payload_text=None,
    )


def _builder_step(builder_json: dict[str, Any], step_id: str) -> dict[str, Any]:
    for step in builder_json.get("steps") or []:
        if isinstance(step, dict) and step.get("id") == step_id:
            return step
    return {}


def _compile_response(flow: IntegrationFlow, test_case: SavedTestCase | None) -> CompileDraftResponse:
    return CompileDraftResponse(
        success=True,
        integration_flow_id=flow.id,
        endpoint_id=flow.endpoint_id,  # type: ignore[arg-type]
        route_id=flow.route_id,  # type: ignore[arg-type]
        saved_test_case_id=test_case.id if test_case else None,
        enabled=flow.enabled,
        endpoint={"method": "POST", "url": master_service.endpoint_url(flow.slug)},
        curl_example=integration_flows_service.curl_example(flow.slug, flow.test_payload_text and "raw_text" or "json", flow.test_payload_text or flow.test_payload_json),
        onec_http_example=integration_flows_service.onec_http_example(flow.slug, "json"),
        next_actions=[
            "Запустите тест.",
            "Проверьте ответ 1С.",
            "Откройте Timeline.",
            "Если всё работает, включите интеграцию.",
        ],
    )


async def _test_case_for_flow(session: AsyncSession, flow: IntegrationFlow) -> SavedTestCase | None:
    if flow.endpoint_id is None:
        return None
    result = await session.execute(select(SavedTestCase).where(SavedTestCase.endpoint_id == flow.endpoint_id).limit(1))
    return result.scalar_one_or_none()


def _matcher_group(contract: InputContract) -> dict[str, Any]:
    operation_key = contract.operation_key
    if operation_key.type in {"endpoint", "none"}:
        return {"mode": "all", "rules": [{"type": "always"}]}
    rules: list[dict[str, Any]] = []
    if operation_key.field_path and operation_key.value is not None:
        rules.append({"type": "body_path_equals", "path": _relative_path(operation_key.field_path), "value": operation_key.value})
    for fallback in operation_key.fallback_paths:
        if operation_key.value is not None:
            rules.append({"type": "body_path_equals", "path": _relative_path(fallback), "value": operation_key.value})
    return {"mode": "any", "rules": rules or [{"type": "always"}]}


def _relative_path(path: str) -> str:
    return path.replace("request.body.", "", 1) if path.startswith("request.body.") else path


def _source_type(source_system: str) -> IntegrationFlowSourceType:
    mapping = {"wms": IntegrationFlowSourceType.WMS, "external_api": IntegrationFlowSourceType.EXTERNAL_API, "webhook": IntegrationFlowSourceType.WEBHOOK, "onec": IntegrationFlowSourceType.ONEC}
    return mapping.get((source_system or "").lower(), IntegrationFlowSourceType.WMS)


def _test_payload_json(contract: InputContract) -> dict[str, Any] | None:
    sample = contract.sample
    if isinstance(sample, dict):
        return sample
    if isinstance(sample, str):
        try:
            parsed = json.loads(sample)
            return parsed if isinstance(parsed, dict) else {"payload": parsed}
        except json.JSONDecodeError:
            return {"payload": sample}
    return {"payload": sample}


def _base_variables(contract: InputContract) -> dict[str, Any]:
    return {"request": _request_variable(contract), "context": {"run_id": "preview-run-001", "event_id": "preview-event-001", "queue_item_id": "preview-queue-item-001"}}


def _request_variable(contract: InputContract) -> dict[str, Any]:
    sample = contract.sample
    if isinstance(sample, str):
        try:
            sample = json.loads(sample)
        except json.JSONDecodeError:
            sample = {"payload": sample}
    return {"body": sample if isinstance(sample, dict) else {"payload": sample}}


def _sample_odata_object(select_fields: list[str]) -> dict[str, Any]:
    fields = select_fields or ["Ref_Key", "Number", "Date", "Posted"]
    sample: dict[str, Any] = {}
    for field in fields:
        lower = field.lower()
        if field.endswith("_Key") or field == "Ref_Key":
            sample[field] = "66666666-6666-6666-6666-666666666666"
        elif lower in {"posted", "проведен"}:
            sample[field] = True
        elif lower in {"date", "дата"}:
            sample[field] = "2026-07-12T12:00:00"
        elif lower in {"number", "номер"}:
            sample[field] = "260666/6938"
        else:
            sample[field] = f"sample_{field}"
    return sample


def _disabled_order_ref(lookup: WmsFactToOneCODataLookupConfig, variables: dict[str, Any]) -> tuple[str | None, list[str]]:
    path = lookup.order_ref_key_path.strip() or "request.body.order_ref_key"
    try:
        value = resolve_template_path(path, variables)
    except PayloadRenderError:
        return None, [f"Если OData lookup отключен, в запросе WMS должен быть Ref_Key заказа: {path}."]
    if value in (None, ""):
        return None, [f"Если OData lookup отключен, в запросе WMS должен быть Ref_Key заказа: {path}."]
    return str(value), []


def _validate_wms_sample(contract: InputContract) -> list[str]:
    source = contract.sample
    if isinstance(source, str):
        try:
            source = json.loads(source)
        except json.JSONDecodeError:
            return []
    if not isinstance(source, dict):
        return []
    items = source.get("items")
    if not isinstance(items, list):
        return ["В запросе WMS нет массива items."]
    operation = str(source.get("operation") or "").strip()
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return [f"Строка items[{index}] должна быть объектом."]
        if operation == "inventory_result":
            if "actual_qty" in item or "actual_quantity" in item:
                continue
            return [f"В строке items[{index}] нет поля actual_qty."]
        if "qty" in item or "quantity" in item:
            continue
        return [f"В строке items[{index}] нет поля qty или quantity."]
    return []


def _operation_label(contract: InputContract) -> str:
    value = _business_value(contract, "request.body.operation") or "warehouse_fact"
    labels = {
        "shipment_fact": "отгрузка",
        "stock_balance": "остатки",
        "inventory_result": "инвентаризация",
        "movement_fact": "перемещение",
    }
    return labels.get(value, value)


def _template_uses_variable(value: Any, variable_name: str) -> bool:
    needle = "{{" + variable_name
    if isinstance(value, str):
        return needle in value
    if isinstance(value, dict):
        return any(_template_uses_variable(item, variable_name) for item in value.values())
    if isinstance(value, list):
        return any(_template_uses_variable(item, variable_name) for item in value)
    return False


def _friendly_odata_error(contract: InputContract, result: ODataStepTestResponse) -> str:
    if result.error_code == "ODATA_RESULT_EMPTY":
        value = _business_value(contract, "request.body.order_number") or "260666/6938"
        return f"Заказ не найден в 1С по номеру {value}."
    return result.message or "OData query не прошёл проверку."


def _business_value(contract: InputContract, preferred_path: str | None = None) -> str | None:
    source = contract.sample
    if isinstance(source, str):
        try:
            source = json.loads(source)
        except json.JSONDecodeError:
            return None
    if not isinstance(source, dict):
        return None
    paths = [preferred_path, contract.business_key.path, *contract.business_key.fallback_paths]
    for path in [item for item in paths if item]:
        if not path.startswith("request.body."):
            continue
        value: Any = source
        for part in path.removeprefix("request.body.").split("."):
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                value = None
                break
        if value not in (None, ""):
            return str(value)
    return None


def _friendly_payload_errors(errors: list[str], known_save_as: list[str]) -> list[str]:
    known = {item.strip() for item in known_save_as if item and item.strip()}
    result: list[str] = []
    for error in errors:
        match = re.search(r"Переменная\s+([^ ]+)\s+не найдена", error)
        if not match:
            result.append(error)
            continue
        variable = match.group(1)
        root = re.split(r"[.\[]", variable, maxsplit=1)[0]
        if root not in known and root not in {"request", "context"}:
            result.append(f"В payload используется {variable}, но переменная {root} не создана. Проверьте OData lookup или Save as предыдущего шага.")
        else:
            result.append(f"В payload используется {variable}, но такого поля нет в данных шага. Проверьте шаблон payload.")
    return result


