from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import IntegrationFlowSourceType, IntegrationFlowTargetType
from app.core.errors import BadRequestError
from app.flow_builder.validator import validate_builder
from app.integration_bus import repository as bus_repository
from app.integration_flows import repository as flow_repository
from app.integration_flows import service as integration_flows_service
from app.integration_flows.models import IntegrationFlow
from app.integration_flows.schemas import EndpointBuilderConfig, IntegrationFlowCreate
from app.integration_master import service as master_service
from app.integration_master.models import IntegrationMasterDraft
from app.integration_master.payload_renderer import PayloadRenderError, render_json_template, resolve_template_path
from app.integration_master.schemas import CompileDraftResponse, CompiledRunTestRequest, InputContract, InputParseRequest
from app.integration_patterns.schemas import (
    XmlRawBridgeCallerResponseConfig,
    XmlRawBridgeCreateResponse,
    XmlRawBridgePatternRequest,
    XmlRawBridgePreviewResponse,
    XmlRawBridgeRunTestRequest,
    XmlRawBridgeRunTestResponse,
    XmlRawBridgeTargetConfig,
)
from app.packages_training.mock_onec_http import accept_raw_xml
from app.test_console.models import SavedTestCase
from app.xml_toolkit import service as xml_service


DEFAULT_XML = """<Документ>
  <Тип>УПД</Тип>
  <Номер>123</Номер>
  <ИНН>7707083893</ИНН>
  <Дата>2026-07-04</Дата>
</Документ>"""


async def preview_pattern(session: AsyncSession, request: XmlRawBridgePatternRequest) -> XmlRawBridgePreviewResponse:
    contract = _contract(request)
    raw_xml = _raw_xml(contract)
    policy = request.raw_xml_policy
    parsed = xml_service.parse(raw_xml)
    hash_preview = xml_service.raw_forward_preview(raw_xml)
    hashes = {
        "original_sha256": hash_preview.input_sha256,
        "forwarded_sha256": hash_preview.forwarded_sha256,
        "unchanged": hash_preview.forwarded_unchanged,
        "size_bytes": hash_preview.size_bytes,
        "comparison_scope": "OMH сравнивает текстовое тело XML после приёма.",
    }
    target_request, target_errors = _target_preview(request.target, raw_xml, hashes)
    target_response = _target_response_sample(request.target, raw_xml)
    variables = _base_variables(contract)
    variables["xml_hashes"] = hashes
    variables[request.target.save_response_as.strip() or "target_response"] = target_response
    variables["target_response"] = target_response
    response_to_caller, caller_errors = _caller_response_preview(request.caller_response, variables, target_response_as=request.target.save_response_as.strip() or "target_response")
    builder_json = _builder_json(request, contract)
    builder_validation = validate_builder(builder_json)
    input_validation = master_service.validate_input_contract(contract)
    validation_disabled = not (policy.require_valid_xml or policy.validate_xml)

    errors = _dedupe(
        [
            *_input_errors(input_validation.get("errors", []), allow_unparsed_xml=validation_disabled),
            *([] if parsed.success or not (policy.require_valid_xml or policy.validate_xml) else ["XML не удалось разобрать. Проверьте структуру документа."]),
            *(target_errors if parsed.success or not (policy.require_valid_xml or policy.validate_xml) else []),
            *caller_errors,
            *[str(item.get("message") or item.get("code")) for item in builder_validation.get("errors", [])],
        ]
    )
    warnings = _dedupe(
        [
            "XML будет переслан как raw text с Content-Type application/xml.",
            *([] if policy.verify_hash else ["Hash check выключен. Для production raw XML bridge рекомендуется включить проверку SHA256."]),
            *([] if parsed.success else ["XML sample invalid, но validation выключен: OMH пересылает текстовое тело без разбора."]),
            *[str(item.get("message") or item.get("code")) for item in builder_validation.get("warnings", [])],
        ]
    )

    return XmlRawBridgePreviewResponse(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        endpoint={"method": "POST", "url": master_service.endpoint_url(contract.slug)},
        incoming_xml=raw_xml,
        xml_paths=[item.model_dump(mode="json") for item in parsed.paths],
        raw_xml_policy=policy.model_dump(mode="json"),
        target_request=target_request,
        target_response=target_response,
        hash_check=hashes,
        response_to_caller=response_to_caller,
        human_steps=[
            "Принят XML от 1С / внешнего сервиса",
            "Сохранён raw XML artifact",
            "Посчитан SHA256 original XML",
            "XML отправлен дальше без изменения",
            "Посчитан SHA256 forwarded XML и сравнен с original",
            "Ответ target возвращён caller-у",
        ],
        advanced={
            "input_contract_validation": input_validation,
            "xml_parse": parsed.model_dump(mode="json"),
            "builder_json": builder_json,
            "builder_validation": builder_validation,
            "variables": variables,
            "target": request.target.model_dump(mode="json"),
            "caller_response": request.caller_response.model_dump(mode="json"),
        },
    )


async def create_pattern(session: AsyncSession, request: XmlRawBridgePatternRequest) -> XmlRawBridgeCreateResponse:
    contract = _contract(request)
    await _ensure_slug_available(session, contract.slug)
    preview = await preview_pattern(session, request)
    if not preview.valid:
        raise BadRequestError("; ".join(preview.errors))

    draft_id = None
    try:
        parse_result = master_service.parse_contract_input(InputParseRequest(input_mode=contract.input_mode, sample=contract.sample, scenario_key=contract.scenario_key))
        draft = await master_service.save_draft(session, contract, parse_result)
        draft_id = draft.id
    except BadRequestError:
        if request.raw_xml_policy.require_valid_xml or request.raw_xml_policy.validate_xml:
            raise

    builder_json = preview.advanced.get("builder_json")
    if not isinstance(builder_json, dict):
        raise BadRequestError("Preview не вернул builder_json для сохранения. Повторите preview и create.")
    flow = await integration_flows_service.create_flow(session, _flow_payload(contract, builder_json, request, enabled=False))
    test_case = await _test_case_for_flow(session, flow)
    if flow.endpoint_id is None or flow.route_id is None:
        raise BadRequestError("Compiled integration was created without endpoint or route. Transaction rolled back.")
    return XmlRawBridgeCreateResponse(draft_id=draft_id, compile=_compile_response(flow, test_case), preview=preview)


async def run_test(session: AsyncSession, request: XmlRawBridgeRunTestRequest) -> XmlRawBridgeRunTestResponse:
    result = await master_service.run_compiled_test(session, request.integration_flow_id, CompiledRunTestRequest(dry_run=request.dry_run))
    return XmlRawBridgeRunTestResponse(**result.model_dump())


def _contract(request: XmlRawBridgePatternRequest) -> InputContract:
    contract = request.input_contract
    slug = request.slug.strip()
    sample = contract.sample if contract.sample not in (None, "") else DEFAULT_XML
    return contract.model_copy(
        update={
            "name": request.name.strip(),
            "slug": slug,
            "input_mode": "xml",
            "source_system": contract.source_system or "onec",
            "scenario_key": contract.scenario_key or "onec_xml_raw_bridge",
            "sample": sample,
            "endpoint_url": master_service.endpoint_url(slug),
        }
    )


def _raw_xml(contract: InputContract) -> str:
    if isinstance(contract.sample, str):
        return contract.sample
    return str(contract.sample or DEFAULT_XML)


def _target_preview(target: XmlRawBridgeTargetConfig, raw_xml: str, hashes: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    connector_name = (target.connector_name or "").strip()
    url = _target_url(target)
    errors: list[str] = []
    if target.mode == "onec_connector" and not connector_name:
        errors.append("Выберите 1C HTTP Service connector или переключитесь в Raw URL.")
    if target.mode == "onec_connector" and not (target.path or "").strip():
        errors.append("Для 1C HTTP Service connector укажите Path, например /receive-upd-xml.")
    if target.mode == "raw_url" and not _valid_http_url(url):
        errors.append("Raw URL должен начинаться с http:// или https://.")
    if not (target.save_response_as or "").strip():
        errors.append("Укажите Save response as для ответа target, например target_response.")
    if errors:
        return None, errors
    return (
        {
            "mode": target.mode,
            "connector": connector_name or None,
            "method": target.method,
            "url": url or None,
            "path": target.path,
            "headers": target.headers,
            "body_type": "xml",
            "body_preview": raw_xml,
            "timeout_seconds": target.timeout_seconds,
            "save_response_as": target.save_response_as,
            **hashes,
        },
        [],
    )


def _target_response_sample(target: XmlRawBridgeTargetConfig, raw_xml: str) -> Any:
    if target.training_mock_onec_xml_receiver:
        return accept_raw_xml(raw_xml)[1]
    if target.mock_response_json is not None:
        return target.mock_response_json
    if target.mock_response_xml is not None:
        return target.mock_response_xml
    if target.mock_response_text is not None:
        return target.mock_response_text
    return {"success": True, "message": "XML accepted", "document_number": _document_number_preview(raw_xml) or "123"}


def _builder_json(request: XmlRawBridgePatternRequest, contract: InputContract) -> dict[str, Any]:
    target = request.target
    return {
        "version": 1,
        "source": {
            "generated_by": "xml_raw_bridge_pattern",
            "pattern_id": "xml_raw_bridge",
            "input_mode": "xml",
            "sample": contract.sample,
            "operation_key": contract.operation_key.model_dump(mode="json"),
            "business_key": contract.business_key.model_dump(mode="json"),
        },
        "steps": [
            {
                "id": "raw_xml_forward",
                "type": "raw_xml_forward",
                "name": "XML отправлен дальше без изменения",
                "source": "request.xml",
                "method": target.method,
                "connector": (target.connector_name or "").strip() or None,
                "url": _target_url(target) if target.mode == "raw_url" else "",
                "base_url": target.base_url,
                "path": target.path,
                "headers": target.headers,
                "timeout_seconds": target.timeout_seconds,
                "save_response_as": target.save_response_as,
                "require_valid_xml": request.raw_xml_policy.require_valid_xml,
                "validate_xml": request.raw_xml_policy.validate_xml,
                "verify_hash": request.raw_xml_policy.verify_hash,
                "training_mock_onec_xml_receiver": target.training_mock_onec_xml_receiver,
                "mock_response_json": target.mock_response_json,
                "mock_response_xml": target.mock_response_xml,
                "mock_response_text": target.mock_response_text,
                "mock_status_code": target.mock_status_code,
            },
            _return_response_step(request.caller_response, target_response_as=target.save_response_as.strip() or "target_response"),
        ],
    }


def _return_response_step(response: XmlRawBridgeCallerResponseConfig, *, target_response_as: str) -> dict[str, Any]:
    if response.type == "accepted_event":
        return {"id": "return_response", "type": "return_response", "name": "Accepted event returned", "status_code": 202, "body": {"accepted": True, "event_id": "{{context.event_id}}", "run_id": "{{context.run_id}}"}, "headers": {"Content-Type": "application/json"}, "response_body_type": "json"}
    if response.type == "proxy_target_response":
        return {"id": "return_response", "type": "return_response", "name": "Target response returned", "status_code": response.status_code, "body": "{{" + target_response_as + "}}", "headers": response.headers, "response_body_type": "json"}
    if response.type == "fixed_success":
        body = response.body or {"success": True, "xml_forwarded": True, "unchanged": "{{xml_hashes.unchanged}}"}
        return {"id": "return_response", "type": "return_response", "name": "Fixed success returned", "status_code": response.status_code, "body": body, "headers": response.headers, "response_body_type": "json"}
    body_type = {"custom_json": "json", "custom_xml": "xml", "custom_raw": "raw_text"}[response.type]
    return {"id": "return_response", "type": "return_response", "name": "Configured caller response", "status_code": response.status_code, "body": response.body, "headers": response.headers, "response_body_type": body_type}


def _caller_response_preview(response: XmlRawBridgeCallerResponseConfig, variables: dict[str, Any], *, target_response_as: str) -> tuple[Any, list[str]]:
    try:
        if response.type == "accepted_event":
            context = variables.get("context") if isinstance(variables.get("context"), dict) else {}
            return {"accepted": True, "event_id": context.get("event_id"), "run_id": context.get("run_id")}, []
        if response.type == "proxy_target_response":
            return resolve_template_path(target_response_as, variables), []
        if response.type == "fixed_success" or response.type == "custom_json":
            return render_json_template(response.body, variables), []
        if response.type in {"custom_xml", "custom_raw"}:
            return response.body, []
        return None, []
    except PayloadRenderError as exc:
        return None, [str(exc)]


def _base_variables(contract: InputContract) -> dict[str, Any]:
    return {
        "request": {"body": {}, "xml": _raw_xml(contract)},
        "context": {"run_id": "preview-run-001", "event_id": "preview-event-001", "queue_item_id": "preview-queue-item-001"},
    }


def _flow_payload(contract: InputContract, builder_json: dict[str, Any], request: XmlRawBridgePatternRequest, *, enabled: bool) -> IntegrationFlowCreate:
    target_step = _builder_step(builder_json, "raw_xml_forward")
    action_json = {
        "type": "call_1c_http_service",
        "operation": "receive_upd_xml",
        "business_object": contract.slug,
        "method": target_step.get("method") or "POST",
        "url": target_step.get("url"),
        "path": target_step.get("path"),
        "target_connector": target_step.get("connector"),
        "body_mode": "xml",
        "response_mode": "sync_response",
        "mock_response_json": target_step.get("mock_response_json"),
        "comment": "Created from XML Raw Bridge pattern wizard",
    }
    return IntegrationFlowCreate(
        name=f"{contract.name} [{contract.slug}]",
        slug=contract.slug,
        description="Created from XML Raw Bridge pattern wizard.",
        enabled=enabled,
        source_type=_source_type(contract.source_system),
        target_type=IntegrationFlowTargetType.ONEC,
        endpoint=EndpointBuilderConfig(input_mode="xml", response_mode="sync_response", auth_mode="none", auth_config_json={}),
        matcher_group_json=_matcher_group(contract),
        action_json=action_json,
        response_config_json={"response_mode": "sync_response", "pattern_id": "xml_raw_bridge", "business_key": contract.business_key.model_dump(mode="json"), "target_response_as": request.target.save_response_as},
        builder_json=builder_json,
        test_payload_json=None,
        test_payload_text=_raw_xml(contract),
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
        curl_example=integration_flows_service.curl_example(flow.slug, "xml", flow.test_payload_text),
        onec_http_example=integration_flows_service.onec_http_example(flow.slug, "xml"),
        next_actions=[
            "Запустите saved test case.",
            "Откройте Timeline и проверьте raw_xml_original.xml, raw_xml_forwarded.xml и xml_hashes.json.",
            "Если hash unchanged=true и target response корректный, включите интеграцию.",
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


def _target_url(target: XmlRawBridgeTargetConfig) -> str:
    if (target.url or "").strip():
        return target.url.strip()
    base = (target.base_url or "").strip().rstrip("/") + "/"
    path = (target.path or "").strip().lstrip("/")
    return urljoin(base, path)


def _valid_http_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def _document_number_preview(raw_xml: str) -> str | None:
    parsed = xml_service.extract(raw_xml, [])
    if not parsed.parsed or not parsed.parsed.success:
        return None
    for path in parsed.parsed.paths:
        if path.path.endswith("/Номер") or path.path.endswith("/Number"):
            return path.value_preview
    return None


def _source_type(source_system: str) -> IntegrationFlowSourceType:
    mapping = {"onec": IntegrationFlowSourceType.ONEC, "external_api": IntegrationFlowSourceType.EXTERNAL_API, "webhook": IntegrationFlowSourceType.WEBHOOK}
    return mapping.get((source_system or "").lower(), IntegrationFlowSourceType.ONEC)


async def _ensure_slug_available(session: AsyncSession, slug: str) -> None:
    master_service.validate_slug(slug)
    draft_result = await session.execute(select(IntegrationMasterDraft.id).where(IntegrationMasterDraft.slug == slug).limit(1))
    if draft_result.scalar_one_or_none() is not None:
        raise BadRequestError(f"Endpoint {master_service.endpoint_url(slug)} уже существует. Выберите другой slug.")
    if await bus_repository.get_endpoint_by_slug(session, slug):
        raise BadRequestError(f"Endpoint {master_service.endpoint_url(slug)} уже существует. Выберите другой slug.")
    if await flow_repository.get_by_slug(session, slug):
        raise BadRequestError(f"Integration Flow со slug {slug} уже существует. Выберите другой slug.")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _input_errors(errors: list[str], *, allow_unparsed_xml: bool) -> list[str]:
    if not allow_unparsed_xml:
        return errors
    ignored_prefixes = (
        "Input Contract должен содержать хотя бы одно поле",
        "Business key path не найден среди полей",
        "Route key path не найден среди полей",
    )
    return [error for error in errors if not error.startswith(ignored_prefixes)]
