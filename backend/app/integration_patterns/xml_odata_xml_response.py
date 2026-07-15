from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import repository as connector_repository
from app.connectors.models import ConnectorInstance
from app.core.enums import IntegrationFlowSourceType, IntegrationFlowTargetType
from app.core.errors import BadRequestError
from app.flow_builder.preview import preview_builder
from app.flow_builder.validator import validate_builder
from app.integration_flows import service as integration_flows_service
from app.integration_flows.models import IntegrationFlow
from app.integration_flows.schemas import EndpointBuilderConfig, IntegrationFlowCreate
from app.integration_master import service as master_service
from app.integration_master.payload_renderer import PayloadRenderError, render_payload_step, resolve_template_path
from app.integration_master.schemas import CompileDraftResponse, CompiledRunTestRequest, InputContract, InputParseRequest, ODataFilterRule, ODataStepConfig, PayloadStepConfig
from app.integration_patterns.schemas import (
    XmlODataXmlExtractField,
    XmlODataXmlResponseCreateResponse,
    XmlODataXmlResponsePatternRequest,
    XmlODataXmlResponsePreviewResponse,
    XmlODataXmlResponseRunTestRequest,
    XmlODataXmlResponseRunTestResponse,
)
from app.odata_explorer import service as odata_explorer_service
from app.odata_explorer.schemas import ODataQueryRequest
from app.test_console.models import SavedTestCase
from app.variables.resolver import render_template
from app.xml_toolkit import service as xml_service
from app.xml_toolkit.schemas import XmlExtractField
from app.integration_patterns._common import (
    default_headers as _default_headers,
    ensure_slug_available as _ensure_slug_available,
    dedupe as _dedupe,
)

DEFAULT_XML = """<Request>
  <Operation>lookup_order</Operation>
  <Number>260666/6938</Number>
  <Format>xml</Format>
</Request>"""

DEFAULT_RESPONSE_TEMPLATE = """<Response>
  <Success>true</Success>
  <Order>
    <UUID>{{order.Ref_Key}}</UUID>
    <Number>{{order.Number}}</Number>
    <Date>{{order.Date}}</Date>
    <Posted>{{order.Posted}}</Posted>
  </Order>
</Response>"""

PLACEHOLDER_RE = re.compile(r"{{\s*([^{}]+?)\s*}}")


async def preview_pattern(session: AsyncSession, request: XmlODataXmlResponsePatternRequest) -> XmlODataXmlResponsePreviewResponse:
    contract = _contract(request)
    raw_xml = _raw_xml(contract)
    parsed = xml_service.parse(raw_xml)
    fields = _extract_fields(request.xml_extract.fields)
    extraction = xml_service.extract(raw_xml, fields) if parsed.success else None
    extracted_values = extraction.values if extraction is not None else {}
    input_validation = master_service.validate_input_contract(contract)
    odata_step, connector = await _normalized_odata_step(session, request.odata_step)
    builder_json = _builder_json(request, contract, odata_step)
    builder_validation = validate_builder(builder_json)

    odata_request, odata_result, odata_response, odata_errors = await _odata_preview(session, odata_step, connector, extracted_values, raw_xml, run_query=parsed.success and extraction is not None and extraction.success)
    variables = _variables_after_odata(contract, extracted_values, odata_step.save_as, odata_result)
    response_to_caller, response_errors = _response_preview(request.response.body_type, request.response.template, variables)
    flow_preview = await preview_builder(session, builder_json, {"xml": raw_xml}, run_real_queries=False) if parsed.success and extraction is not None and extraction.success else {"valid": False, "errors": []}

    errors = _dedupe(
        [
            *input_validation.get("errors", []),
            *([] if parsed.success else ["XML не удалось разобрать. Проверьте структуру документа."]),
            *_friendly_extract_errors(extraction.errors if extraction is not None else []),
            *odata_errors,
            *(response_errors if not odata_errors else []),
            *[str(item.get("message") or item.get("code")) for item in builder_validation.get("errors", [])],
        ]
    )
    warnings = _dedupe(
        [
            *[str(item.get("message") or item.get("code")) for item in builder_validation.get("warnings", [])],
            *([] if request.response.body_type == "xml" else ["Ответ caller-у настроен не как XML. Это допустимо, но основной сценарий паттерна — XML-ответ."]),
        ]
    )

    return XmlODataXmlResponsePreviewResponse(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        endpoint={"method": "POST", "url": master_service.endpoint_url(contract.slug)},
        incoming_xml=raw_xml,
        xml_paths=[item.model_dump(mode="json") for item in parsed.paths],
        extracted_variables=extracted_values,
        odata_request=odata_request,
        odata_result=odata_result,
        response_to_caller=response_to_caller,
        human_steps=[
            "Получен XML-запрос",
            "Из XML извлечены поля",
            "Выполнен OData-запрос",
            "Собран XML-ответ" if request.response.body_type == "xml" else "Собран ответ",
            "Ответ возвращён вызывающей системе",
        ],
        advanced={
            "input_contract_validation": input_validation,
            "xml_parse": parsed.model_dump(mode="json"),
            "xml_extract": extraction.model_dump(mode="json") if extraction is not None else None,
            "odata_response": odata_response,
            "builder_json": builder_json,
            "builder_validation": builder_validation,
            "flow_preview": flow_preview,
            "variables_after_extract": _base_variables(contract, extracted_values),
            "variables_after_odata": variables,
        },
    )


async def create_pattern(session: AsyncSession, request: XmlODataXmlResponsePatternRequest) -> XmlODataXmlResponseCreateResponse:
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
    flow = await integration_flows_service.create_flow(session, _flow_payload(contract, builder_json, request, enabled=False))
    test_case = await _test_case_for_flow(session, flow)
    if flow.endpoint_id is None or flow.route_id is None:
        raise BadRequestError("Compiled integration was created without endpoint or route. Transaction rolled back.")
    return XmlODataXmlResponseCreateResponse(draft_id=draft.id, compile=_compile_response(flow, test_case), preview=preview)


async def run_test(session: AsyncSession, request: XmlODataXmlResponseRunTestRequest) -> XmlODataXmlResponseRunTestResponse:
    result = await master_service.run_compiled_test(session, request.integration_flow_id, CompiledRunTestRequest(dry_run=request.dry_run))
    return XmlODataXmlResponseRunTestResponse(**result.model_dump())


def _contract(request: XmlODataXmlResponsePatternRequest) -> InputContract:
    slug = request.slug.strip()
    contract = request.input_contract
    sample = contract.sample if contract.sample not in (None, "") else DEFAULT_XML
    fields = list(contract.fields)
    if not fields:
        try:
            parsed = master_service.parse_contract_input(InputParseRequest(input_mode="xml", sample=sample, scenario_key="xml_input_odata_xml_response"))
            fields = parsed.fields
        except BadRequestError:
            fields = []
    operation_key = contract.operation_key
    if operation_key.type == "field" and not operation_key.field_path:
        operation_key = operation_key.model_copy(update={"field_path": "xml./Request/Operation", "value": "lookup_order"})
    business_key = contract.business_key
    if not business_key.path:
        business_key = business_key.model_copy(update={"path": "xml./Request/Number"})
    return contract.model_copy(
        update={
            "name": request.name.strip(),
            "slug": slug,
            "input_mode": "xml",
            "source_system": contract.source_system or "external_api",
            "scenario_key": contract.scenario_key or "xml_input_odata_xml_response",
            "sample": sample,
            "fields": fields,
            "operation_key": operation_key,
            "business_key": business_key,
            "endpoint_url": master_service.endpoint_url(slug),
        }
    )


def _raw_xml(contract: InputContract) -> str:
    return contract.sample if isinstance(contract.sample, str) else str(contract.sample or DEFAULT_XML)


def _extract_fields(fields: list[XmlODataXmlExtractField]) -> list[XmlExtractField]:
    return [XmlExtractField(name=field.name, path=_xml_path(field.path), required=field.required, mode=field.mode) for field in fields]


def _xml_path(path: str) -> str:
    clean = path.removeprefix("xml.").strip()
    return clean if clean.startswith("/") else "/" + clean.strip("/")


async def _normalized_odata_step(session: AsyncSession, step: ODataStepConfig) -> tuple[ODataStepConfig, ConnectorInstance | None]:
    connector: ConnectorInstance | None = None
    connection_name = (step.connection_name or "").strip()
    if step.connection_id:
        connector = await connector_repository.get_instance(session, step.connection_id)
        if connector is not None:
            connection_name = connector.name
    elif connection_name:
        connector = await connector_repository.get_by_name(session, connection_name)
    normalized = step.model_copy(update={"connection_name": connection_name or step.connection_name})
    return normalized, connector


async def _odata_preview(
    session: AsyncSession,
    step: ODataStepConfig,
    connector: ConnectorInstance | None,
    extracted_values: dict[str, Any],
    raw_xml: str,
    *,
    run_query: bool,
) -> tuple[dict[str, Any], Any, dict[str, Any] | None, list[str]]:
    errors = _validate_odata_config(step, connector)
    variables = _base_variables_from_xml(raw_xml, extracted_values)
    template_filter = _compile_step_filter(step)
    rendered_filter: str | None = None
    if template_filter:
        try:
            rendered_filter = _render_odata_template(template_filter, variables)
        except BadRequestError as exc:
            errors.append(str(exc))
    query = _odata_query(step, rendered_filter)
    request_preview = {
        "connection": step.connection_name or None,
        "resource": step.resource,
        "template_filter": template_filter,
        "rendered_filter": rendered_filter,
        "template_url": _odata_url(step.resource, template_filter, step),
        "rendered_url": _odata_url(step.resource, rendered_filter, step),
        "query": query,
        "save_as": step.save_as,
    }
    if errors or not run_query:
        return request_preview, None, None, errors
    try:
        result = await odata_explorer_service.query(
            session,
            step.connection_id or connector.id,  # type: ignore[union-attr,arg-type]
            ODataQueryRequest(
                resource=step.resource,
                top=step.top,
                filter=rendered_filter,
                select=",".join(step.select) if step.select else None,
                orderby=step.orderby,
                paginate=step.paginate,
            ),
        )
    except BadRequestError as exc:
        return request_preview, None, None, [str(exc)]
    items = [item for item in (result.get("items") if isinstance(result.get("items"), list) else []) if isinstance(item, dict)]
    request_preview["request"] = result.get("request") if isinstance(result.get("request"), dict) else {}
    request_preview["request_url"] = result.get("request_url")
    if not items and step.required:
        return request_preview, None, result, [_friendly_empty_odata(step, extracted_values)]
    saved: Any = items[0] if int(step.top or 1) == 1 else items
    return request_preview, saved, result, []


def _validate_odata_config(step: ODataStepConfig, connector: ConnectorInstance | None) -> list[str]:
    errors: list[str] = []
    if step.connection_id is None and not (step.connection_name or "").strip():
        errors.append("Выберите OData-подключение.")
    elif connector is None:
        errors.append(f"OData-подключение {step.connection_name or step.connection_id} не найдено.")
    elif connector.connector_type != "onec":
        errors.append(f"Connector {connector.name} должен быть connector_type=onec.")
    if not step.resource.strip():
        errors.append("Укажите Resource OData, например Document_ЗаказКлиента.")
    if not (step.save_as or "").strip():
        errors.append("Укажите Save as для результата OData, например order.")
    if step.top is not None and (step.top < 1 or step.top > 500):
        errors.append("$top должен быть от 1 до 500.")
    return errors


def _compile_step_filter(step: ODataStepConfig) -> str | None:
    if step.filter_mode == "raw":
        return (step.filter or "").strip() or None
    if step.filter_rule:
        return _compile_filter_rule(step.filter_rule)
    return (step.filter or "").strip() or None


def _compile_filter_rule(rule: ODataFilterRule) -> str:
    field = rule.field.strip()
    if not field:
        return ""
    value = _odata_literal(rule.value, rule.value_type)
    if rule.operator == "contains":
        return f"contains({field}, {value})"
    return f"{field} {rule.operator} {value}"


def _odata_literal(value: Any, value_type: str) -> str:
    if value_type == "raw":
        return str(value or "")
    if value_type == "number":
        return str(value)
    if value_type == "boolean":
        return "true" if str(value).lower() in {"true", "1", "yes", "да"} else "false"
    if value_type == "variable":
        placeholder = str(value or "").strip()
        if not placeholder.startswith("{{"):
            placeholder = "{{" + placeholder + "}}"
        return f"'{placeholder}'"
    if value_type == "guid":
        placeholder = str(value or "").strip()
        if placeholder.startswith("{{"):
            return f"guid'{placeholder}'"
        return f"guid'{_escape_odata_string(placeholder)}'"
    return f"'{_escape_odata_string(str(value or ''))}'"


def _render_odata_template(template: str, variables: dict[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        expression = match.group(1).strip()
        try:
            value = resolve_template_path(expression, variables)
        except PayloadRenderError as exc:
            raise BadRequestError(f"В OData filter используется переменная {expression}, но она не была извлечена из XML.") from exc
        return _escape_odata_string(str(value))

    return PLACEHOLDER_RE.sub(replace, template)


def _escape_odata_string(value: str) -> str:
    return value.replace("'", "''")


def _odata_query(step: ODataStepConfig, rendered_filter: str | None) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if rendered_filter:
        query["$filter"] = rendered_filter
    if step.select:
        query["$select"] = ",".join(step.select)
    if step.top:
        query["$top"] = step.top
    if step.orderby:
        query["$orderby"] = step.orderby
    return query


def _odata_url(resource: str, rendered_filter: str | None, step: ODataStepConfig) -> str:
    query = _odata_query(step, rendered_filter)
    if not query:
        return resource
    return f"{resource}?{urlencode(query, doseq=False)}"


def _response_preview(body_type: str, template: Any, variables: dict[str, Any]) -> tuple[Any, list[str]]:
    try:
        payload_step = PayloadStepConfig(type="build_payload", body_type=body_type, save_as="target_payload", json_mode="raw_template", template=template, fields=[], dynamic_entries=[])
        return render_payload_step(payload_step, variables).rendered_body, []
    except PayloadRenderError as exc:
        return None, [_friendly_payload_error(exc)]


def _friendly_payload_error(exc: PayloadRenderError) -> str:
    if exc.code == "PAYLOAD_XML_INVALID":
        return "Не удалось собрать XML-ответ. Проверьте закрывающие теги и переменные."
    match = re.search(r"Переменная\s+([^ ]+)\s+не найдена", exc.message)
    if match:
        variable = match.group(1)
        root = variable.split(".", 1)[0]
        return f"В шаблоне ответа используется {variable}, но переменная {root} не создана."
    return exc.message


def _variables_after_odata(contract: InputContract, extracted: dict[str, Any], save_as: str, odata_result: Any) -> dict[str, Any]:
    variables = _base_variables(contract, extracted)
    if odata_result is not None:
        variables[save_as.strip() or "order"] = odata_result
    return variables


def _base_variables(contract: InputContract, extracted: dict[str, Any]) -> dict[str, Any]:
    return {
        "request": {"body": {}, "xml": _raw_xml(contract)},
        "context": {"run_id": "preview-run-001", "event_id": "preview-event-001", "queue_item_id": "preview-queue-item-001"},
        "xml_fields": extracted,
        **extracted,
    }


def _base_variables_from_xml(raw_xml: str, extracted: dict[str, Any]) -> dict[str, Any]:
    return {"request": {"body": {}, "xml": raw_xml}, "xml_fields": extracted, **extracted}


def _builder_json(request: XmlODataXmlResponsePatternRequest, contract: InputContract, odata_step: ODataStepConfig) -> dict[str, Any]:
    return {
        "version": 1,
        "source": {
            "generated_by": "xml_odata_xml_response_pattern",
            "pattern_id": "xml_odata_xml_response",
            "input_mode": "xml",
            "sample": contract.sample,
            "operation_key": contract.operation_key.model_dump(mode="json"),
            "business_key": contract.business_key.model_dump(mode="json"),
            "human_labels": [
                "Получен XML-запрос",
                "Из XML извлечены поля",
                "Выполнен OData-запрос",
                "Собран XML-ответ",
                "Ответ возвращён вызывающей системе",
            ],
        },
        "steps": [
            {
                "id": "extract_xml_fields",
                "type": "xml_extract",
                "name": "Из XML извлечены поля",
                "source": "request.xml",
                "raw_artifact_name": "raw_xml_input.xml",
                "fields": [field.model_dump(mode="json", exclude={"example"}) for field in request.xml_extract.fields],
            },
            {
                "id": "query_odata",
                "type": "odata_query",
                "name": "Выполнен OData-запрос",
                "connection": odata_step.connection_name or str(odata_step.connection_id or ""),
                "resource": odata_step.resource,
                "filter": _compile_step_filter(odata_step),
                "select": odata_step.select,
                "top": odata_step.top,
                "orderby": odata_step.orderby,
                "paginate": odata_step.paginate,
                "save_as": odata_step.save_as,
                "required": odata_step.required,
            },
            {
                "id": "build_response",
                "type": "build_payload",
                "name": "Собран XML-ответ" if request.response.body_type == "xml" else "Собран ответ",
                "body_type": request.response.body_type,
                "save_as": "target_payload",
                "json_mode": "raw_template",
                "template": request.response.template or DEFAULT_RESPONSE_TEMPLATE,
                "fields": [],
                "dynamic_entries": [],
                "response_artifacts": True,
            },
            _return_response_step(request),
        ],
    }


def _return_response_step(request: XmlODataXmlResponsePatternRequest) -> dict[str, Any]:
    step = {
        "id": "return_response",
        "type": "return_response",
        "name": "Ответ возвращён вызывающей системе",
        "status_code": request.response.status_code,
        "headers": {**_default_headers(request.response.body_type), **request.response.headers},
        "response_body_type": request.response.body_type,
    }
    if request.response.body_type == "xml":
        step["body_template"] = "{{target_payload}}"
    else:
        step["body"] = "{{target_payload}}"
    return step


def _flow_payload(contract: InputContract, builder_json: dict[str, Any], request: XmlODataXmlResponsePatternRequest, *, enabled: bool) -> IntegrationFlowCreate:
    return IntegrationFlowCreate(
        name=f"{contract.name} [{contract.slug}]",
        slug=contract.slug,
        description="Created from XML -> OData -> XML/JSON Response pattern wizard.",
        enabled=enabled,
        source_type=_source_type(contract.source_system),
        target_type=IntegrationFlowTargetType.INTERNAL,
        endpoint=EndpointBuilderConfig(input_mode="xml", response_mode="sync_response", auth_mode="none", auth_config_json={}),
        matcher_group_json=_matcher_group(contract),
        action_json={"type": "return_response", "operation": "xml_odata_xml_response", "business_object": contract.slug, "body_mode": request.response.body_type, "response_mode": "sync_response", "comment": "Created from XML -> OData -> XML/JSON Response wizard"},
        response_config_json={"response_mode": "sync_response", "pattern_id": "xml_odata_xml_response", "business_key": contract.business_key.model_dump(mode="json"), "response": request.response.model_dump(mode="json")},
        builder_json=builder_json,
        test_payload_json=None,
        test_payload_text=_raw_xml(contract),
    )


def _matcher_group(contract: InputContract) -> dict[str, Any]:
    operation_key = contract.operation_key
    if operation_key.type in {"endpoint", "none"}:
        return {"mode": "all", "rules": [{"type": "always"}]}
    rules: list[dict[str, Any]] = []
    if operation_key.field_path and operation_key.value is not None:
        rules.append(_xml_rule(operation_key.field_path, operation_key.value))
    for fallback in operation_key.fallback_paths:
        if operation_key.value is not None:
            rules.append(_xml_rule(fallback, operation_key.value))
    return {"mode": "any", "rules": [rule for rule in rules if rule] or [{"type": "always"}]}


def _xml_rule(path: str, value: Any) -> dict[str, Any]:
    return {"type": "xml_path_equals", "path": _xml_matcher_path(path), "value": value}


def _xml_matcher_path(path: str) -> str:
    clean = path.removeprefix("xml.").strip()
    if clean.startswith("/"):
        return ".".join(part for part in clean.split("/") if part)
    return clean.replace("/", ".")


def _compile_response(flow: IntegrationFlow, test_case: SavedTestCase | None) -> CompileDraftResponse:
    return CompileDraftResponse(
        success=True,
        integration_flow_id=flow.id,
        endpoint_id=flow.endpoint_id,  # type: ignore[arg-type]
        route_id=flow.route_id,  # type: ignore[arg-type]
        saved_test_case_id=test_case.id if test_case else None,
        enabled=flow.enabled,
        endpoint={"method": "POST", "url": master_service.endpoint_url(flow.slug)},
        curl_example=integration_flows_service.curl_example(flow.slug, "xml", flow.test_payload_text),
        onec_http_example=integration_flows_service.onec_http_example(flow.slug, "xml"),
        next_actions=[
            "Запустите saved test case.",
            "Проверьте XML-ответ и artifacts raw_xml_input.xml, xml_extracted_fields.json, odata_query_request.json, odata_query_response.json, response_template.xml, rendered_response.xml.",
            "Если ответ корректный, включите интеграцию.",
        ],
    )


async def _test_case_for_flow(session: AsyncSession, flow: IntegrationFlow) -> SavedTestCase | None:
    if flow.endpoint_id is None:
        return None
    result = await session.execute(select(SavedTestCase).where(SavedTestCase.endpoint_id == flow.endpoint_id).limit(1))
    return result.scalar_one_or_none()


def _source_type(source_system: str) -> IntegrationFlowSourceType:
    mapping = {"onec": IntegrationFlowSourceType.ONEC, "1c": IntegrationFlowSourceType.ONEC, "external_api": IntegrationFlowSourceType.EXTERNAL_API, "webhook": IntegrationFlowSourceType.WEBHOOK}
    return mapping.get((source_system or "").lower(), IntegrationFlowSourceType.EXTERNAL_API)


def _friendly_extract_errors(errors: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for error in errors:
        path = error.get("path")
        if error.get("code") == "XML_REQUIRED_FIELD_MISSING" and path:
            result.append(f"В XML не найдено поле {path}.")
        else:
            result.append(str(error.get("message") or error.get("code") or error))
    return result


def _friendly_empty_odata(step: ODataStepConfig, extracted: dict[str, Any]) -> str:
    value = extracted.get("order_number") or extracted.get("number") or extracted.get("inn") or next((item for item in extracted.values() if item not in (None, "")), None)
    if "Заказ" in step.resource or "Order" in step.resource:
        return f"Заказ не найден по номеру {value}." if value else "Заказ не найден по OData filter."
    if "Контрагент" in step.resource:
        return f"Контрагент не найден по ИНН {value}." if value else "Контрагент не найден по OData filter."
    return f"OData не вернул записей по значению {value}." if value else "OData не вернул записей."


