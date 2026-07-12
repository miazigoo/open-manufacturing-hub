from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID
from urllib.parse import urljoin

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import IntegrationFlowSourceType, IntegrationFlowTargetType
from app.core.errors import BadRequestError, NotFoundError
from app.flow_builder.compiler import FlowCompiler
from app.flow_builder.validator import validate_builder
from app.integration_bus import repository as bus_repository
from app.integration_flows import repository as flow_repository
from app.integration_flows import service as integration_flows_service
from app.integration_flows.models import IntegrationFlow
from app.integration_flows.schemas import EndpointBuilderConfig, IntegrationFlowCreate
from app.integration_master import service as master_service
from app.integration_master.models import IntegrationMasterDraft
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
from app.odata_connections import service as odata_connections_service
from app.test_console.models import SavedTestCase
from app.integration_patterns.schemas import (
    SourceWebApiWritebackCallerResponseConfig,
    SourceWebApiWritebackEndpointConfig,
    SourceWebApiWritebackExtractionConfig,
    SourceWebApiWritebackOneCCreateResponse,
    SourceWebApiWritebackOneCPatternRequest,
    SourceWebApiWritebackOneCPreviewResponse,
    SourceWebApiWritebackOneCRunTestRequest,
    SourceWebApiWritebackOneCRunTestResponse,
    SourceWebApiWritebackOneCServiceConfig,
)


SITE_DEFAULT_RESPONSE = {"success": True, "external_id": "SITE-ORDER-123", "status": "accepted"}
ONEC_DEFAULT_RESPONSE = {"success": True, "message": "External id saved"}


async def preview_pattern(session: AsyncSession, request: SourceWebApiWritebackOneCPatternRequest) -> SourceWebApiWritebackOneCPreviewResponse:
    contract = _contract(request)
    odata_step = request.odata_step
    site_payload_step = _payload_step(request.site_payload, "site_payload")
    site_endpoint = request.site_endpoint
    extraction = request.site_response_extraction
    onec_payload_step = _payload_step(request.onec_writeback_payload, "onec_writeback_payload")
    onec_service = request.onec_http_service

    input_validation = master_service.validate_input_contract(contract)
    odata_preview = master_service.preview_odata_step(ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=odata_step))
    odata_test = await master_service.test_odata_step(session, ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=odata_step))
    odata_result = odata_test.result_preview if odata_test.success else None

    variables_after_odata = _base_variables(contract)
    variables_after_odata[odata_step.save_as.strip() or "order"] = odata_result or _sample_odata_object(odata_step.select)

    site_payload_preview = master_service.preview_payload_step(PayloadStepRequest(input_contract=contract, previous_variables=variables_after_odata, payload_step=site_payload_step))
    variables_after_site_payload = dict(variables_after_odata)
    if site_payload_preview.valid:
        variables_after_site_payload[site_payload_step.save_as] = site_payload_preview.rendered_body

    site_request, site_request_errors = _endpoint_preview(site_endpoint, variables_after_site_payload, default_body_source=site_payload_step.save_as)
    site_response = _site_response_sample(site_endpoint, extraction)
    variables_after_site_response = dict(variables_after_site_payload)
    variables_after_site_response[site_endpoint.save_response_as.strip() or "site_response"] = site_response

    extraction_preview, extraction_errors = _extraction_preview(extraction, variables_after_site_response)

    onec_payload_preview = master_service.preview_payload_step(PayloadStepRequest(input_contract=contract, previous_variables=variables_after_site_response, payload_step=onec_payload_step))
    variables_after_onec_payload = dict(variables_after_site_response)
    if onec_payload_preview.valid:
        variables_after_onec_payload[onec_payload_step.save_as] = onec_payload_preview.rendered_body

    onec_request, onec_request_errors = _onec_service_preview(onec_service, variables_after_onec_payload, default_body_source=onec_payload_step.save_as)
    onec_response = _onec_response_sample(onec_service)
    variables_after_onec_response = dict(variables_after_onec_payload)
    variables_after_onec_response[onec_service.save_response_as.strip() or "onec_writeback_response"] = onec_response

    caller_response, caller_errors = _caller_response_preview(
        request.caller_response,
        variables_after_onec_response,
        site_response_as=site_endpoint.save_response_as.strip() or "site_response",
        onec_response_as=onec_service.save_response_as.strip() or "onec_writeback_response",
    )
    builder_json = await _builder_json(session, request, contract, odata_preview.template_filter or odata_step.filter)
    builder_validation = validate_builder(builder_json)

    errors = _dedupe(
        [
            *input_validation.get("errors", []),
            *([] if odata_preview.valid else odata_preview.errors),
            *([] if odata_test.success else [_friendly_odata_error(contract, odata_test)]),
            *_friendly_payload_errors(site_payload_preview.errors, [odata_step.save_as]),
            *site_request_errors,
            *extraction_errors,
            *_friendly_payload_errors(onec_payload_preview.errors, [odata_step.save_as, site_endpoint.save_response_as]),
            *onec_request_errors,
            *caller_errors,
            *[str(item.get("message") or item.get("code")) for item in builder_validation.get("errors", [])],
        ]
    )
    warnings = _dedupe([*odata_preview.warnings, *site_payload_preview.warnings, *onec_payload_preview.warnings, *[str(item.get("message") or item.get("code")) for item in builder_validation.get("warnings", [])]])

    return SourceWebApiWritebackOneCPreviewResponse(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        endpoint={"method": "POST", "url": master_service.endpoint_url(contract.slug)},
        incoming_request=contract.sample,
        odata_request={
            "resource": odata_preview.rendered_resource,
            "template_filter": odata_preview.template_filter,
            "rendered_filter": odata_preview.rendered_filter,
            "template_url": odata_preview.template_url,
            "rendered_url": odata_preview.rendered_url,
            "request": odata_test.request,
            "save_as": odata_preview.saved_as,
        },
        odata_result=odata_result,
        site_payload=site_payload_preview.rendered_body if site_payload_preview.valid else None,
        site_request=site_request,
        site_response=site_response,
        extraction=extraction_preview,
        onec_writeback_payload=onec_payload_preview.rendered_body if onec_payload_preview.valid else None,
        onec_writeback_request=onec_request,
        onec_writeback_response=onec_response,
        response_to_caller=caller_response,
        human_steps=[
            "Получен запрос",
            "Найден заказ в 1С",
            "Собран payload для сайта",
            "Отправлено на сайт",
            "Получен external_id",
            "Собран payload для 1С",
            "Ответ записан в 1С",
            "Ответ возвращён вызывающей системе",
        ],
        advanced={
            "input_contract_validation": input_validation,
            "odata_preview": odata_preview.model_dump(mode="json"),
            "odata_test": odata_test.model_dump(mode="json"),
            "site_payload_step": site_payload_step.model_dump(mode="json"),
            "site_payload_preview": site_payload_preview.model_dump(mode="json"),
            "site_endpoint": site_endpoint.model_dump(mode="json"),
            "extraction": extraction.model_dump(mode="json"),
            "onec_writeback_payload_step": onec_payload_step.model_dump(mode="json"),
            "onec_writeback_payload_preview": onec_payload_preview.model_dump(mode="json"),
            "onec_http_service": onec_service.model_dump(mode="json"),
            "caller_response": request.caller_response.model_dump(mode="json"),
            "builder_json": builder_json,
            "builder_validation": builder_validation,
            "variables_after_odata": variables_after_odata,
            "variables_after_site_payload": variables_after_site_payload,
            "variables_after_site_response": variables_after_site_response,
            "variables_after_onec_payload": variables_after_onec_payload,
            "variables_after_onec_response": variables_after_onec_response,
        },
    )


async def create_pattern(session: AsyncSession, request: SourceWebApiWritebackOneCPatternRequest) -> SourceWebApiWritebackOneCCreateResponse:
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
    flow_payload = _flow_payload(contract, builder_json, enabled=False, comment="Created from Source -> Web API -> Write Back to 1C pattern wizard")
    flow = await integration_flows_service.create_flow(session, flow_payload)
    test_case = await _test_case_for_flow(session, flow)
    if flow.endpoint_id is None or flow.route_id is None:
        raise BadRequestError("Compiled integration was created without endpoint or route. Transaction rolled back.")
    return SourceWebApiWritebackOneCCreateResponse(draft_id=draft.id, compile=_compile_response(flow, test_case), preview=preview)


async def run_test(session: AsyncSession, request: SourceWebApiWritebackOneCRunTestRequest) -> SourceWebApiWritebackOneCRunTestResponse:
    result = await master_service.run_compiled_test(session, request.integration_flow_id, CompiledRunTestRequest(dry_run=request.dry_run))
    return SourceWebApiWritebackOneCRunTestResponse(**result.model_dump())


def _contract(request: SourceWebApiWritebackOneCPatternRequest) -> InputContract:
    contract = request.input_contract
    return contract.model_copy(
        update={
            "name": request.name.strip(),
            "slug": request.slug.strip(),
            "scenario_key": contract.scenario_key or "onec_publish_order_to_site",
            "endpoint_url": master_service.endpoint_url(request.slug.strip()),
        }
    )


def _payload_step(payload: PayloadStepConfig, default_save_as: str) -> PayloadStepConfig:
    save_as = (payload.save_as or default_save_as).strip() or default_save_as
    return payload.model_copy(update={"save_as": save_as, "overwrite": True})


async def _builder_json(session: AsyncSession, request: SourceWebApiWritebackOneCPatternRequest, contract: InputContract, odata_filter: str | None) -> dict[str, Any]:
    odata_step = await _with_connection_name(session, request.odata_step)
    site_payload = _payload_step(request.site_payload, "site_payload")
    onec_payload = _payload_step(request.onec_writeback_payload, "onec_writeback_payload")
    site_endpoint = request.site_endpoint
    onec_service = request.onec_http_service
    caller_response = request.caller_response
    condition = request.site_response_extraction.success_condition
    return {
        "version": 1,
        "source": {
            "generated_by": "source_web_api_writeback_onec_pattern",
            "pattern_id": "source_web_api_writeback_onec",
            "input_mode": contract.input_mode,
            "sample": contract.sample,
            "operation_key": contract.operation_key.model_dump(mode="json"),
            "business_key": contract.business_key.model_dump(mode="json"),
        },
        "steps": [
            {
                "id": "find_order",
                "type": "odata_query",
                "name": "Найден заказ в 1С",
                "connection": odata_step.connection_name or str(odata_step.connection_id or ""),
                "resource": odata_step.resource,
                "filter": odata_filter,
                "select": odata_step.select,
                "top": odata_step.top,
                "orderby": odata_step.orderby,
                "paginate": odata_step.paginate,
                "save_as": odata_step.save_as,
                "required": odata_step.required,
            },
            _payload_builder_step("build_site_payload", "Собран payload для сайта", site_payload),
            _call_endpoint_step("send_site_api", "Отправлено на сайт", site_endpoint, body_source=site_payload.save_as, mock_response=_site_response_sample(site_endpoint, request.site_response_extraction)),
            {
                "id": "validate_site_response",
                "type": "condition",
                "name": "Сайт принял данные",
                "if": _condition_expression(condition),
                "else": "fail",
                "error_message": "Внешний сайт не принял данные. Оригинальный ответ сохранён в Timeline.",
            },
            {
                "id": "validate_site_external_id",
                "type": "condition",
                "name": "Получен external_id",
                "if": f"{request.site_response_extraction.external_id_path} exists",
                "else": "fail",
                "error_message": "Сайт ответил успешно, но в ответе нет external_id. Проверьте путь site_response.external_id.",
            },
            _payload_builder_step("build_onec_writeback_payload", "Собран payload для 1С", onec_payload),
            _call_onec_step("writeback_onec", "Ответ записан в 1С", onec_service, body_source=onec_payload.save_as),
            _return_response_step(caller_response, site_response_as=site_endpoint.save_response_as.strip() or "site_response", onec_response_as=onec_service.save_response_as.strip() or "onec_writeback_response"),
        ],
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


def _call_endpoint_step(step_id: str, name: str, endpoint: SourceWebApiWritebackEndpointConfig, *, body_source: str, mock_response: Any) -> dict[str, Any]:
    return {
        "id": step_id,
        "type": "call_endpoint",
        "name": name,
        "method": endpoint.method,
        "url": endpoint.url,
        "headers": endpoint.headers,
        "body": _body_template(endpoint.body_source or body_source, endpoint.custom_body),
        "body_type": endpoint.body_type,
        "timeout_seconds": endpoint.timeout_seconds,
        "save_response_as": endpoint.save_response_as,
        "mock_response_json": endpoint.mock_response_json if endpoint.mock_response_json is not None else mock_response,
    }


def _call_onec_step(step_id: str, name: str, service: SourceWebApiWritebackOneCServiceConfig, *, body_source: str) -> dict[str, Any]:
    return {
        "id": step_id,
        "type": "call_endpoint",
        "name": name,
        "method": service.method,
        "connector": service.connector_name,
        "url": _onec_url(service),
        "path": service.path,
        "headers": service.headers,
        "body": _body_template(service.body_source or body_source, None),
        "body_type": service.body_type,
        "timeout_seconds": service.timeout_seconds,
        "save_response_as": service.save_response_as,
        "mock_response_json": service.mock_response_json if service.mock_response_json is not None else ONEC_DEFAULT_RESPONSE,
    }


def _return_response_step(response: SourceWebApiWritebackCallerResponseConfig, *, site_response_as: str, onec_response_as: str) -> dict[str, Any]:
    if response.type == "accepted_event":
        return {"id": "return_response", "type": "return_response", "name": "Ответ возвращён вызывающей системе", "status_code": 202, "body": {"accepted": True, "event_id": "{{context.event_id}}", "run_id": "{{context.run_id}}"}, "headers": response.headers, "response_body_type": "json"}
    if response.type == "site_response":
        body: Any = "{{" + site_response_as + "}}"
    elif response.type == "onec_writeback_response":
        body = "{{" + onec_response_as + "}}"
    else:
        body = response.body
    return {"id": "return_response", "type": "return_response", "name": "Ответ возвращён вызывающей системе", "status_code": response.status_code, "body": body, "headers": response.headers, "response_body_type": "json"}


def _body_template(body_source: str, custom_body: Any = None) -> Any:
    if body_source == "none":
        return ""
    if body_source == "custom":
        return custom_body if custom_body is not None else ""
    return "{{" + body_source + "}}"


def _condition_expression(condition: Any) -> str:
    value = condition.value
    if isinstance(value, bool):
        right = "true" if value else "false"
    elif isinstance(value, (int, float)):
        right = str(value)
    else:
        right = json.dumps(value, ensure_ascii=False)
    operator = "!=" if condition.operator == "ne" else "=="
    return f"{condition.path} {operator} {right}"


def _endpoint_preview(endpoint: SourceWebApiWritebackEndpointConfig, variables: dict[str, Any], *, default_body_source: str) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    url = (endpoint.url or "").strip()
    if not _valid_http_url(url):
        errors.append("URL сайта должен начинаться с http:// или https://.")
    if not (endpoint.save_response_as or "").strip():
        errors.append("Укажите Save response as для ответа сайта, например site_response.")
    body, body_errors = _render_body(endpoint.body_source or default_body_source, endpoint.custom_body, variables)
    errors.extend(body_errors)
    return ({"method": endpoint.method, "url": url, "headers": render_json_template(endpoint.headers, variables), "body_type": endpoint.body_type, "body_preview": body, "timeout_seconds": endpoint.timeout_seconds, "save_response_as": endpoint.save_response_as} if not errors else None), errors


def _onec_service_preview(service: SourceWebApiWritebackOneCServiceConfig, variables: dict[str, Any], *, default_body_source: str) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    url = _onec_url(service)
    if not _valid_http_url(url):
        errors.append("URL 1С HTTP service должен начинаться с http:// или https://.")
    if not (service.save_response_as or "").strip():
        errors.append("Укажите Save response as для ответа 1С, например onec_writeback_response.")
    body, body_errors = _render_body(service.body_source or default_body_source, None, variables)
    errors.extend(body_errors)
    return ({"method": service.method, "url": url, "path": service.path, "headers": render_json_template(service.headers, variables), "body_type": service.body_type, "body_preview": body, "timeout_seconds": service.timeout_seconds, "save_response_as": service.save_response_as} if not errors else None), errors


def _render_body(body_source: str, custom_body: Any, variables: dict[str, Any]) -> tuple[Any, list[str]]:
    try:
        if body_source == "none":
            return None, []
        if body_source == "custom":
            return render_json_template(custom_body, variables), []
        return resolve_template_path(body_source, variables), []
    except PayloadRenderError as exc:
        return None, [str(exc)]


def _extraction_preview(extraction: SourceWebApiWritebackExtractionConfig, variables: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    external_id = _safe_resolve(extraction.external_id_path, variables)
    status = _safe_resolve(extraction.status_path, variables)
    success_value = _safe_resolve(extraction.success_condition.path, variables)
    expected = extraction.success_condition.value
    success_ok = success_value != expected if extraction.success_condition.operator == "ne" else success_value == expected
    if not success_ok:
        errors.append("Внешний сайт не принял данные. Оригинальный ответ сохранён в Timeline.")
    if external_id in (None, ""):
        errors.append("Сайт ответил успешно, но в ответе нет external_id. Проверьте путь site_response.external_id.")
    return {"external_id": external_id, "status": status, "success_value": success_value, "success": success_ok, "external_id_path": extraction.external_id_path, "status_path": extraction.status_path}, errors


def _caller_response_preview(response: SourceWebApiWritebackCallerResponseConfig, variables: dict[str, Any], *, site_response_as: str, onec_response_as: str) -> tuple[Any, list[str]]:
    try:
        if response.type == "accepted_event":
            context = variables.get("context") if isinstance(variables.get("context"), dict) else {}
            return {"accepted": True, "event_id": context.get("event_id"), "run_id": context.get("run_id")}, []
        if response.type == "site_response":
            return resolve_template_path(site_response_as, variables), []
        if response.type == "onec_writeback_response":
            return resolve_template_path(onec_response_as, variables), []
        return render_json_template(response.body, variables), []
    except PayloadRenderError as exc:
        return None, [str(exc)]


def _safe_resolve(path: str, variables: dict[str, Any]) -> Any:
    try:
        return resolve_template_path(path, variables)
    except PayloadRenderError:
        return None


def _site_response_sample(endpoint: SourceWebApiWritebackEndpointConfig, extraction: SourceWebApiWritebackExtractionConfig) -> dict[str, Any]:
    if isinstance(endpoint.mock_response_json, dict):
        return endpoint.mock_response_json
    return extraction.sample_response or SITE_DEFAULT_RESPONSE


def _onec_response_sample(service: SourceWebApiWritebackOneCServiceConfig) -> dict[str, Any]:
    return service.mock_response_json if isinstance(service.mock_response_json, dict) else ONEC_DEFAULT_RESPONSE


def _onec_url(service: SourceWebApiWritebackOneCServiceConfig) -> str:
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


def _flow_payload(contract: InputContract, builder_json: dict[str, Any], *, enabled: bool, comment: str) -> IntegrationFlowCreate:
    slug = contract.slug
    name = f"{contract.name} [{slug}]"
    response_mode = "sync_response"
    matcher_group = _matcher_group(contract)
    writeback_step = _builder_step(builder_json, "writeback_onec")
    action_json = {
        "type": "call_1c_http_service",
        "operation": "source_web_api_writeback_onec",
        "business_object": slug,
        "method": writeback_step.get("method") or "POST",
        "url": writeback_step.get("url"),
        "body_mode": writeback_step.get("body_type") or "json",
        "response_mode": response_mode,
        "comment": comment,
    }
    return IntegrationFlowCreate(
        name=name,
        slug=slug,
        description=f"Created from Source -> Web API -> Write Back to 1C pattern wizard. {comment}",
        enabled=enabled,
        source_type=_source_type(contract.source_system),
        target_type=IntegrationFlowTargetType.ONEC,
        endpoint=EndpointBuilderConfig(input_mode=contract.input_mode, response_mode=response_mode, auth_mode="none", auth_config_json={}),
        matcher_group_json=matcher_group,
        action_json=action_json,
        response_config_json={
            "response_mode": response_mode,
            "pattern_id": "source_web_api_writeback_onec",
            "business_key": contract.business_key.model_dump(mode="json"),
            "site_response_as": _builder_step(builder_json, "send_site_api").get("save_response_as"),
            "onec_writeback_response_as": writeback_step.get("save_response_as"),
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
            "Запустите тест и проверьте, что сайт вернул external_id.",
            "Проверьте, что 1С приняла запись external_id.",
            "Откройте Timeline и проверьте outgoing API call и writeback call.",
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
    mapping = {"onec": IntegrationFlowSourceType.ONEC, "1c": IntegrationFlowSourceType.ONEC, "wms": IntegrationFlowSourceType.WMS, "website": IntegrationFlowSourceType.WEBSITE, "external_api": IntegrationFlowSourceType.EXTERNAL_API, "webhook": IntegrationFlowSourceType.WEBHOOK}
    return mapping.get((source_system or "").lower(), IntegrationFlowSourceType.EXTERNAL_API)


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
    if contract.input_mode == "json":
        sample = contract.sample
        if isinstance(sample, str):
            try:
                sample = json.loads(sample)
            except json.JSONDecodeError:
                sample = {"payload": sample}
        return {"body": sample if isinstance(sample, dict) else {"payload": sample}}
    if contract.input_mode == "raw_text":
        return {"body": {}, "raw_text": str(contract.sample or "")}
    return {"body": {}, "xml": str(contract.sample or "")}


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


async def _ensure_slug_available(session: AsyncSession, slug: str) -> None:
    master_service.validate_slug(slug)
    draft_result = await session.execute(select(IntegrationMasterDraft.id).where(IntegrationMasterDraft.slug == slug).limit(1))
    if draft_result.scalar_one_or_none() is not None:
        raise BadRequestError(f"Endpoint {master_service.endpoint_url(slug)} уже существует. Выберите другой slug.")
    if await bus_repository.get_endpoint_by_slug(session, slug):
        raise BadRequestError(f"Endpoint {master_service.endpoint_url(slug)} уже существует. Выберите другой slug.")
    if await flow_repository.get_by_slug(session, slug):
        raise BadRequestError(f"Integration Flow со slug {slug} уже существует. Выберите другой slug.")


def _friendly_odata_error(contract: InputContract, result: ODataStepTestResponse) -> str:
    if result.error_code == "ODATA_RESULT_EMPTY":
        value = _business_value(contract) or "260666/6938"
        return f"Заказ не найден в 1С по номеру {value}."
    return result.message or "OData query не прошёл проверку."


def _business_value(contract: InputContract) -> str | None:
    source = contract.sample
    if isinstance(source, str):
        try:
            source = json.loads(source)
        except json.JSONDecodeError:
            return None
    if not isinstance(source, dict):
        return None
    paths = [contract.business_key.path, *contract.business_key.fallback_paths]
    for path in paths:
        if not path or not path.startswith("request.body."):
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
            result.append(f"В payload используется {variable}, но переменная {root} не создана. Проверьте Save as предыдущих шагов.")
        else:
            result.append(f"В payload используется {variable}, но такого поля нет в данных шага. Проверьте шаблон payload.")
    return result


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
