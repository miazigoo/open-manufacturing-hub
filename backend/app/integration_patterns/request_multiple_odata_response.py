from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError
from app.integration_bus import repository as bus_repository
from app.integration_flows import repository as flow_repository
from app.integration_master import service as master_service
from app.integration_master.models import IntegrationMasterDraft
from app.integration_master.schemas import (
    CompileDraftRequest,
    CompiledRunTestRequest,
    FinalActionConfig,
    FinalActionRequest,
    FinalActionReturnConfig,
    InputContract,
    InputParseRequest,
    ODataObjectStepRequest,
    ODataObjectStepTestResponse,
    ODataStepRequest,
    ODataStepTestResponse,
    PayloadStepConfig,
    PayloadStepRequest,
)
from app.integration_patterns.schemas import (
    RequestMultipleODataResponseCreateResponse,
    RequestMultipleODataResponsePatternRequest,
    RequestMultipleODataResponsePreviewResponse,
    RequestMultipleODataResponseResponseConfig,
    RequestMultipleODataResponseRunTestRequest,
    RequestMultipleODataResponseRunTestResponse,
)


async def preview_pattern(session: AsyncSession, request: RequestMultipleODataResponsePatternRequest) -> RequestMultipleODataResponsePreviewResponse:
    contract = _contract(request)
    find_order = request.find_order
    read_items = request.read_items
    payload_step = _payload_step(request.response)
    final_action = _final_action(request.response)

    input_validation = master_service.validate_input_contract(contract)

    order_preview = master_service.preview_odata_step(ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=find_order))
    order_test = await master_service.test_odata_step(session, ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=find_order))
    order_result = order_test.result_preview if order_test.success else None
    variables_after_order = _base_variables(contract)
    variables_after_order[find_order.save_as.strip() or "order"] = order_result or _sample_order(find_order.select)

    items_preview = master_service.preview_odata_object_step(ODataObjectStepRequest(input_contract=contract, previous_variables=variables_after_order, odata_object_step=read_items))
    items_test = await master_service.test_odata_object_step(session, ODataObjectStepRequest(input_contract=contract, previous_variables=variables_after_order, odata_object_step=read_items))
    items_result = items_test.result_preview if items_test.success else []
    variables_after_items = dict(variables_after_order)
    variables_after_items[read_items.save_as.strip() or "items"] = items_result or _sample_items(read_items.select)

    payload_preview = master_service.preview_payload_step(PayloadStepRequest(input_contract=contract, previous_variables=variables_after_items, payload_step=payload_step))
    variables_after_payload = dict(variables_after_items)
    if payload_preview.valid:
        variables_after_payload[payload_step.save_as] = payload_preview.rendered_body
    final_preview = master_service.preview_final_action_step(FinalActionRequest(input_contract=contract, previous_variables=variables_after_payload, final_action=final_action))

    errors = _dedupe(
        [
            *input_validation.get("errors", []),
            *([] if order_preview.valid else order_preview.errors),
            *([] if order_test.success else [_friendly_order_error(contract, order_test)]),
            *([] if items_preview.valid else items_preview.errors),
            *([] if items_test.success else [_friendly_items_error(items_test)]),
            *_friendly_payload_errors(payload_preview.errors, payload_preview.error_code, request.response.type, read_items.save_as),
            *([] if payload_preview.valid else []),
            *(final_preview.errors if payload_preview.valid else []),
        ]
    )
    warnings = _dedupe([*order_preview.warnings, *items_preview.warnings, *payload_preview.warnings, *final_preview.warnings])

    return RequestMultipleODataResponsePreviewResponse(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        endpoint={"method": "POST", "url": master_service.endpoint_url(contract.slug)},
        incoming_request=contract.sample,
        order_request={
            "resource": order_preview.rendered_resource,
            "template_filter": order_preview.template_filter,
            "rendered_filter": order_preview.rendered_filter,
            "template_url": order_preview.template_url,
            "rendered_url": order_preview.rendered_url,
            "request": order_test.request,
            "save_as": order_preview.saved_as,
        },
        order_result=order_result,
        items_request={
            "template_resource": items_preview.template_resource,
            "rendered_resource": items_preview.rendered_resource,
            "template_filter": items_preview.template_filter,
            "rendered_filter": items_preview.rendered_filter,
            "template_url": items_preview.template_url,
            "rendered_url": items_preview.rendered_url,
            "request": items_test.request,
            "save_as": items_preview.saved_as,
            "items_count": items_test.items_count,
        },
        items_result=items_result,
        response_to_caller=final_preview.caller_response_preview if payload_preview.valid else None,
        human_steps=[
            "Получен запрос",
            "Найден заказ в 1С",
            "Прочитаны строки заказа",
            "Собран XML-ответ" if request.response.type == "xml" else "Собран ответ",
            "Ответ возвращён вызывающему сервису",
        ],
        advanced={
            "input_contract_validation": input_validation,
            "order_preview": order_preview.model_dump(mode="json"),
            "order_test": order_test.model_dump(mode="json"),
            "items_preview": items_preview.model_dump(mode="json"),
            "items_test": items_test.model_dump(mode="json"),
            "payload_step": payload_step.model_dump(mode="json"),
            "payload_preview": payload_preview.model_dump(mode="json"),
            "final_action": final_action.model_dump(mode="json"),
            "final_preview": final_preview.model_dump(mode="json"),
            "variables_after_order": variables_after_order,
            "variables_after_items": variables_after_items,
            "variables_after_payload": variables_after_payload,
        },
    )


async def create_pattern(session: AsyncSession, request: RequestMultipleODataResponsePatternRequest) -> RequestMultipleODataResponseCreateResponse:
    contract = _contract(request)
    await _ensure_slug_available(session, contract.slug)
    preview = await preview_pattern(session, request)
    if not preview.valid:
        raise BadRequestError("; ".join(preview.errors))

    parse_result = master_service.parse_contract_input(InputParseRequest(input_mode=contract.input_mode, sample=contract.sample, scenario_key=contract.scenario_key))
    draft = await master_service.save_draft(session, contract, parse_result)
    draft, _ = await master_service.append_odata_step(session, draft.id, request.find_order)

    variables_after_order = preview.advanced.get("variables_after_order")
    variables_after_items = preview.advanced.get("variables_after_items")
    variables_after_payload = preview.advanced.get("variables_after_payload")
    if not all(isinstance(value, dict) for value in [variables_after_order, variables_after_items, variables_after_payload]):
        raise BadRequestError("Preview не вернул переменные для сохранения. Повторите preview и create.")

    draft, _ = await master_service.append_odata_object_step(session, draft.id, request.read_items, variables_after_order)  # type: ignore[arg-type]
    draft, _ = await master_service.append_payload_step(session, draft.id, _payload_step(request.response), variables_after_items)  # type: ignore[arg-type]
    draft, _ = await master_service.save_final_action(session, draft.id, _final_action(request.response), variables_after_payload)  # type: ignore[arg-type]
    compiled = await master_service.compile_draft(
        session,
        draft.id,
        CompileDraftRequest(enabled=False, create_saved_test_case=True, comment="Created from Request -> Multiple OData -> Response wizard"),
    )
    return RequestMultipleODataResponseCreateResponse(draft_id=draft.id, compile=compiled, preview=preview)


async def run_test(session: AsyncSession, request: RequestMultipleODataResponseRunTestRequest) -> RequestMultipleODataResponseRunTestResponse:
    result = await master_service.run_compiled_test(session, request.integration_flow_id, CompiledRunTestRequest(dry_run=request.dry_run))
    return RequestMultipleODataResponseRunTestResponse(**result.model_dump())


def _contract(request: RequestMultipleODataResponsePatternRequest) -> InputContract:
    contract = request.input_contract
    return contract.model_copy(
        update={
            "name": request.name.strip(),
            "slug": request.slug.strip(),
            "scenario_key": contract.scenario_key or "external_order_lookup_xml_response",
            "endpoint_url": master_service.endpoint_url(request.slug.strip()),
        }
    )


def _payload_step(response: RequestMultipleODataResponseResponseConfig) -> PayloadStepConfig:
    template = response.template if response.template not in (None, "") else _default_template(response.type)
    if response.type == "json":
        payload_template = template
    else:
        payload_template = template if isinstance(template, str) else json.dumps(template, ensure_ascii=False, indent=2)
    return PayloadStepConfig(
        type="build_payload",
        body_type=response.type,
        save_as="target_payload",
        json_mode="raw_template",
        template=payload_template,
        fields=[],
        dynamic_entries=[],
        overwrite=True,
    )


def _final_action(response: RequestMultipleODataResponseResponseConfig) -> FinalActionConfig:
    return_type = {"json": "custom_json", "xml": "custom_xml", "raw_text": "custom_raw"}[response.type]
    return FinalActionConfig(
        type="return_response",
        method="POST",
        url=None,
        headers={},
        body_type=response.type,
        body_source="target_payload",
        custom_body=None,
        timeout_seconds=30,
        return_to_caller=FinalActionReturnConfig(
            type=return_type,
            body=None,
            status_code=response.status_code,
            headers={**_default_headers(response.type), **response.headers},
        ),
    )


def _base_variables(contract: InputContract) -> dict[str, Any]:
    return {
        "request": _request_variable(contract),
        "context": {"run_id": "preview-run-001", "event_id": "preview-event-001", "queue_item_id": "preview-queue-item-001"},
    }


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


def _sample_order(select_fields: list[str]) -> dict[str, Any]:
    return _sample_object(select_fields or ["Ref_Key", "Number", "Date", "Posted"])


def _sample_items(select_fields: list[str]) -> list[dict[str, Any]]:
    fields = select_fields or ["Номенклатура_Key", "Количество", "Цена", "Сумма"]
    return [
        _sample_object(fields, key="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", amount_index=1),
        _sample_object(fields, key="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", amount_index=2),
    ]


def _sample_object(select_fields: list[str], *, key: str = "66666666-6666-6666-6666-666666666666", amount_index: int = 1) -> dict[str, Any]:
    sample: dict[str, Any] = {}
    for field in select_fields:
        lower = field.lower()
        if field == "Ref_Key" or field.endswith("_Key"):
            sample[field] = key
        elif lower in {"number", "номер"}:
            sample[field] = "260666/6938"
        elif lower in {"date", "дата"}:
            sample[field] = "2026-07-12T12:00:00"
        elif lower in {"posted", "проведен"}:
            sample[field] = True
        elif "количество" in lower:
            sample[field] = 2 * amount_index
        elif lower in {"цена", "price"}:
            sample[field] = 120.5 * amount_index
        elif lower in {"сумма", "amount"}:
            sample[field] = 241.0 * amount_index
        else:
            sample[field] = f"sample_{field}"
    return sample


def _default_template(body_type: str) -> Any:
    if body_type == "json":
        return {
            "success": True,
            "order": {
                "uuid": "{{order.Ref_Key}}",
                "number": "{{order.Number}}",
                "date": "{{order.Date}}",
                "posted": "{{order.Posted}}",
            },
            "items": "{{items}}",
        }
    if body_type == "raw_text":
        return "OK order={{order.Number}} items={{items.length}}"
    return """<Response>
  <Success>true</Success>
  <Order>
    <UUID>{{order.Ref_Key}}</UUID>
    <Number>{{order.Number}}</Number>
    <Date>{{order.Date}}</Date>
    <Posted>{{order.Posted}}</Posted>
  </Order>
  <Items>
    {{#items}}
    <Item>
      <ProductUUID>{{Номенклатура_Key}}</ProductUUID>
      <Quantity>{{Количество}}</Quantity>
      <Price>{{Цена}}</Price>
      <Amount>{{Сумма}}</Amount>
    </Item>
    {{/items}}
  </Items>
</Response>"""


def _default_headers(body_type: str) -> dict[str, Any]:
    if body_type == "xml":
        return {"Content-Type": "application/xml; charset=utf-8"}
    if body_type == "raw_text":
        return {"Content-Type": "text/plain; charset=utf-8"}
    return {"Content-Type": "application/json"}


async def _ensure_slug_available(session: AsyncSession, slug: str) -> None:
    master_service.validate_slug(slug)
    draft_result = await session.execute(select(IntegrationMasterDraft.id).where(IntegrationMasterDraft.slug == slug).limit(1))
    if draft_result.scalar_one_or_none() is not None:
        raise BadRequestError(f"Endpoint {master_service.endpoint_url(slug)} уже существует. Выберите другой slug.")
    if await bus_repository.get_endpoint_by_slug(session, slug):
        raise BadRequestError(f"Endpoint {master_service.endpoint_url(slug)} уже существует. Выберите другой slug.")
    if await flow_repository.get_by_slug(session, slug):
        raise BadRequestError(f"Integration Flow со slug {slug} уже существует. Выберите другой slug.")


def _friendly_order_error(contract: InputContract, result: ODataStepTestResponse) -> str:
    message = result.message or "OData query не прошёл проверку."
    if result.error_code == "ODATA_RESULT_EMPTY":
        value = _business_value(contract) or "260666/6938"
        return f"Заказ не найден по номеру {value}. Проверьте OData-подключение, ресурс и номер заказа."
    if result.error_code == "ODATA_QUERY_FAILED" and re.search(r"\b(401|403|unauthorized|forbidden)\b", message, re.I):
        return "1С не приняла логин или пароль. Проверьте OData-подключение."
    return message


def _friendly_items_error(result: ODataObjectStepTestResponse) -> str:
    if result.error_code == "ODATA_TABULAR_PART_EMPTY":
        return "Табличная часть Товары пустая или недоступна через OData."
    return result.message or "Не удалось прочитать табличную часть Товары."


def _friendly_payload_errors(errors: list[str], error_code: str | None, body_type: str, items_save_as: str) -> list[str]:
    result: list[str] = []
    for error in errors:
        match = re.search(r"Переменная\s+([^ ]+)\s+не найдена", error)
        variable = match.group(1) if match else ""
        root = re.split(r"[.\[]", variable, maxsplit=1)[0] if variable else ""
        if root == "items" and (items_save_as or "items").strip() != "items":
            result.append("В XML-шаблоне используется items, но шаг чтения строк сохранил результат под другим именем.")
        elif body_type == "xml" and (error_code in {"PAYLOAD_XML_INVALID", "PAYLOAD_XML_LOOP_NOT_ARRAY", "VARIABLE_NOT_FOUND"} or match):
            result.append("Не удалось собрать XML-ответ. Проверьте переменные order и items.")
        else:
            result.append(error)
    return result


def _business_value(contract: InputContract) -> str | None:
    paths = [contract.business_key.path, *contract.business_key.fallback_paths]
    source = contract.sample
    if isinstance(source, str):
        try:
            source = json.loads(source)
        except json.JSONDecodeError:
            return None
    if not isinstance(source, dict):
        return None
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


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
