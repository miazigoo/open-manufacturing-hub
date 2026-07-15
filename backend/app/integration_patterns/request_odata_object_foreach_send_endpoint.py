from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError
from app.integration_master import service as master_service
from app.integration_master.schemas import (
    CompileDraftRequest,
    CompiledRunTestRequest,
    FinalActionConfig,
    FinalActionRequest,
    FinalActionReturnConfig,
    ForeachODataStepRequest,
    ForeachODataStepTestResponse,
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
    RequestODataObjectForeachSendEndpointCreateResponse,
    RequestODataObjectForeachSendEndpointPatternRequest,
    RequestODataObjectForeachSendEndpointPreviewResponse,
    RequestODataObjectForeachSendEndpointRunTestRequest,
    RequestODataObjectForeachSendEndpointRunTestResponse,
    RequestODataSendEndpointResponseConfig,
    RequestODataSendEndpointTargetConfig,
)
from app.integration_patterns._common import (
    request_variable as _request_variable,
    ensure_slug_available as _ensure_slug_available,
    dedupe as _dedupe,
)


async def preview_pattern(session: AsyncSession, request: RequestODataObjectForeachSendEndpointPatternRequest) -> RequestODataObjectForeachSendEndpointPreviewResponse:
    contract = _contract(request)
    find_order = request.find_order
    read_products = request.read_products
    find_codes = request.find_codes
    payload_step = _payload_step(request.payload)
    final_action = _final_action(request.target, request.response_to_caller)

    input_validation = master_service.validate_input_contract(contract)

    order_preview = master_service.preview_odata_step(ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=find_order))
    order_test = await master_service.test_odata_step(session, ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=find_order))
    order_result = order_test.result_preview if order_test.success else None
    variables_after_order = _base_variables(contract)
    variables_after_order[find_order.save_as.strip() or "order"] = order_result or _sample_order(find_order.select)

    products_preview = master_service.preview_odata_object_step(ODataObjectStepRequest(input_contract=contract, previous_variables=variables_after_order, odata_object_step=read_products))
    products_test = await master_service.test_odata_object_step(session, ODataObjectStepRequest(input_contract=contract, previous_variables=variables_after_order, odata_object_step=read_products))
    products_result = products_test.result_preview if products_test.success else []
    variables_after_products = dict(variables_after_order)
    variables_after_products[read_products.save_as.strip() or "products"] = products_result or _sample_products(read_products.select)

    codes_preview = master_service.preview_foreach_odata_step(ForeachODataStepRequest(input_contract=contract, previous_variables=variables_after_products, foreach_step=find_codes))
    codes_test = await master_service.test_foreach_odata_step(session, ForeachODataStepRequest(input_contract=contract, previous_variables=variables_after_products, foreach_step=find_codes))
    codes_result = codes_test.result_body if codes_test.success else None
    variables_after_codes = dict(variables_after_products)
    variables_after_codes[find_codes.save_as.strip() or "codes"] = codes_result if codes_result is not None else _sample_codes(find_codes.select)

    payload_preview = master_service.preview_payload_step(PayloadStepRequest(input_contract=contract, previous_variables=variables_after_codes, payload_step=payload_step))
    variables_after_payload = dict(variables_after_codes)
    if payload_preview.valid:
        variables_after_payload[payload_step.save_as] = payload_preview.rendered_body
    final_preview = master_service.preview_final_action_step(FinalActionRequest(input_contract=contract, previous_variables=variables_after_payload, final_action=final_action))

    errors = _dedupe(
        [
            *input_validation.get("errors", []),
            *([] if order_preview.valid else order_preview.errors),
            *([] if order_test.success else [_friendly_order_error(contract, order_test)]),
            *([] if products_preview.valid else products_preview.errors),
            *([] if products_test.success else [_friendly_products_error(products_test)]),
            *([] if codes_preview.valid else _friendly_foreach_validation_errors(codes_preview.errors)),
            *([] if codes_test.success else [_friendly_codes_error(codes_test)]),
            *_friendly_payload_errors(payload_preview.errors, [find_order.save_as, read_products.save_as, find_codes.save_as]),
            *_friendly_final_action_errors(final_preview.errors, payload_step.save_as),
        ]
    )
    warnings = _dedupe(
        [
            *order_preview.warnings,
            *products_preview.warnings,
            *codes_preview.warnings,
            *payload_preview.warnings,
            *final_preview.warnings,
            *_foreach_warnings(find_codes.top, find_codes.paginate),
        ]
    )

    return RequestODataObjectForeachSendEndpointPreviewResponse(
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
        products_request={
            "template_resource": products_preview.template_resource,
            "rendered_resource": products_preview.rendered_resource,
            "template_url": products_preview.template_url,
            "rendered_url": products_preview.rendered_url,
            "request": products_test.request,
            "save_as": products_preview.saved_as,
            "items_count": products_test.items_count,
        },
        products_result=products_result,
        codes_requests=codes_test.requests,
        codes_result=codes_result,
        codes_summary={
            "source_count": codes_test.source_count,
            "items_processed": codes_test.items_processed,
            "odata_requests": codes_test.odata_requests,
            "rows_found": codes_test.rows_found,
            "preview": codes_test.result_preview,
            "truncated_note": _codes_truncated_note(codes_test.rows_found),
        },
        target_payload=payload_preview.rendered_body if payload_preview.valid else None,
        target_request=final_preview.send_preview,
        response_to_caller=final_preview.caller_response_preview,
        human_steps=[
            "Получен запрос от DnP",
            "Найден заказ производства в 1С",
            "Прочитана продукция заказа",
            "Найдены коды Честного знака",
            "Собран JSON для DnP",
            f"Отправлено в DnP: {final_action.method} {final_action.url}",
            "Ответ возвращён вызывающему сервису",
        ],
        advanced={
            "input_contract_validation": input_validation,
            "order_preview": order_preview.model_dump(mode="json"),
            "order_test": order_test.model_dump(mode="json"),
            "products_preview": products_preview.model_dump(mode="json"),
            "products_test": products_test.model_dump(mode="json"),
            "codes_preview": codes_preview.model_dump(mode="json"),
            "codes_test": codes_test.model_dump(mode="json"),
            "payload_step": payload_step.model_dump(mode="json"),
            "payload_preview": payload_preview.model_dump(mode="json"),
            "final_action": final_action.model_dump(mode="json"),
            "final_preview": final_preview.model_dump(mode="json"),
            "variables_after_order": variables_after_order,
            "variables_after_products": variables_after_products,
            "variables_after_codes": variables_after_codes,
            "variables_after_payload": variables_after_payload,
        },
    )


async def create_pattern(session: AsyncSession, request: RequestODataObjectForeachSendEndpointPatternRequest) -> RequestODataObjectForeachSendEndpointCreateResponse:
    contract = _contract(request)
    await _ensure_slug_available(session, contract.slug)
    preview = await preview_pattern(session, request)
    if not preview.valid:
        raise BadRequestError("; ".join(preview.errors))

    parse_result = master_service.parse_contract_input(InputParseRequest(input_mode=contract.input_mode, sample=contract.sample, scenario_key=contract.scenario_key))
    draft = await master_service.save_draft(session, contract, parse_result)
    draft, _ = await master_service.append_odata_step(session, draft.id, request.find_order)

    variables_after_order = preview.advanced.get("variables_after_order")
    variables_after_products = preview.advanced.get("variables_after_products")
    variables_after_codes = preview.advanced.get("variables_after_codes")
    variables_after_payload = preview.advanced.get("variables_after_payload")
    if not all(isinstance(value, dict) for value in [variables_after_order, variables_after_products, variables_after_codes, variables_after_payload]):
        raise BadRequestError("Preview не вернул переменные для сохранения. Повторите preview и create.")

    draft, _ = await master_service.append_odata_object_step(session, draft.id, request.read_products, variables_after_order)  # type: ignore[arg-type]
    draft, _ = await master_service.append_foreach_odata_step(session, draft.id, request.find_codes, variables_after_products)  # type: ignore[arg-type]
    draft, _ = await master_service.append_payload_step(session, draft.id, _payload_step(request.payload), variables_after_codes)  # type: ignore[arg-type]
    draft, _ = await master_service.save_final_action(session, draft.id, _final_action(request.target, request.response_to_caller), variables_after_payload)  # type: ignore[arg-type]
    compiled = await master_service.compile_draft(
        session,
        draft.id,
        CompileDraftRequest(enabled=False, create_saved_test_case=True, comment="Created from DnP CHZ code pool pattern wizard"),
    )
    return RequestODataObjectForeachSendEndpointCreateResponse(draft_id=draft.id, compile=compiled, preview=preview)


async def run_test(session: AsyncSession, request: RequestODataObjectForeachSendEndpointRunTestRequest) -> RequestODataObjectForeachSendEndpointRunTestResponse:
    result = await master_service.run_compiled_test(session, request.integration_flow_id, CompiledRunTestRequest(dry_run=request.dry_run))
    return RequestODataObjectForeachSendEndpointRunTestResponse(**result.model_dump())


def _contract(request: RequestODataObjectForeachSendEndpointPatternRequest) -> InputContract:
    contract = request.input_contract
    return contract.model_copy(
        update={
            "name": request.name.strip(),
            "slug": request.slug.strip(),
            "scenario_key": contract.scenario_key or "dnp_chz_code_pool",
            "endpoint_url": master_service.endpoint_url(request.slug.strip()),
        }
    )


def _payload_step(payload: PayloadStepConfig) -> PayloadStepConfig:
    save_as = (payload.save_as or "target_payload").strip() or "target_payload"
    return payload.model_copy(update={"save_as": save_as, "overwrite": True})


def _final_action(target: RequestODataSendEndpointTargetConfig, response: RequestODataSendEndpointResponseConfig) -> FinalActionConfig:
    return FinalActionConfig(
        type="send_endpoint",
        method=target.method,
        url=target.url,
        headers=target.headers,
        body_type=target.body_type,
        body_source=target.body_source,
        custom_body=target.custom_body,
        timeout_seconds=target.timeout_seconds,
        return_to_caller=FinalActionReturnConfig(
            type=response.type,
            body=response.body,
            status_code=response.status_code,
            headers=response.headers,
        ),
    )


def _base_variables(contract: InputContract) -> dict[str, Any]:
    return {
        "request": _request_variable(contract),
        "context": {"run_id": "preview-run-001", "event_id": "preview-event-001", "queue_item_id": "preview-queue-item-001"},
    }


def _sample_order(select_fields: list[str]) -> dict[str, Any]:
    return _sample_object(select_fields or ["Ref_Key", "Number", "Date", "Posted"], number="260666/6938")


def _sample_products(select_fields: list[str]) -> list[dict[str, Any]]:
    fields = select_fields or ["Номенклатура_Key", "Количество", "КоличествоУпаковок"]
    return [_sample_object(fields, key="ff22288c-2da4-11f1-8388-000c29b755c7")]


def _sample_codes(select_fields: list[str]) -> list[dict[str, Any]]:
    fields = select_fields or ["КодМаркировки", "ПолныйКодМаркировки", "Номенклатура_Key", "ДокументОснование"]
    return [_sample_object(fields, key="ff22288c-2da4-11f1-8388-000c29b755c7", code_index=index) for index in range(1, 4)]


def _sample_object(select_fields: list[str], *, key: str = "c3335ee4-43d0-11f1-8388-000c29b755c7", number: str = "260666/6938", code_index: int = 1) -> dict[str, Any]:
    sample: dict[str, Any] = {}
    for field in select_fields:
        lower = field.lower()
        if field == "Ref_Key" or field.endswith("_Key"):
            sample[field] = key
        elif "основание" in lower:
            sample[field] = "c3335ee4-43d0-11f1-8388-000c29b755c7"
        elif lower in {"number", "номер"}:
            sample[field] = number
        elif lower in {"date", "дата"}:
            sample[field] = "2026-04-29T16:38:53"
        elif lower in {"posted", "проведен"}:
            sample[field] = True
        elif "количество" in lower:
            sample[field] = 180
        elif "полныйкод" in lower:
            sample[field] = f"0104607009529011215DnP{code_index:03d}"
        elif "кодмаркировки" in lower:
            sample[field] = f"CHZ-{code_index:03d}"
        elif lower == "gtin":
            sample[field] = "04607009529011"
        elif lower == "статус":
            sample[field] = "emitted"
        else:
            sample[field] = f"sample_{field}"
    return sample


def _friendly_order_error(contract: InputContract, result: ODataStepTestResponse) -> str:
    message = result.message or "OData query не прошёл проверку."
    if result.error_code == "ODATA_RESULT_EMPTY":
        value = _business_value(contract) or _sample_number(contract)
        return f"Заказ производства не найден по Number = {value}. Проверьте номер заказа и OData-подключение."
    if result.error_code == "ODATA_QUERY_FAILED" and re.search(r"\b(401|403|unauthorized|forbidden)\b", message, re.I):
        return "1С не приняла логин или пароль. Проверьте OData-подключение."
    return message


def _friendly_products_error(result: ODataObjectStepTestResponse) -> str:
    if result.error_code == "ODATA_TABULAR_PART_EMPTY":
        return "В заказе не найдена табличная часть Продукция или она пустая."
    return result.message or "Не удалось прочитать табличную часть Продукция."


def _friendly_codes_error(result: ForeachODataStepTestResponse) -> str:
    if result.error_code == "FOREACH_ODATA_RESULT_EMPTY":
        return "По продукции не найдено кодов Честного знака. Проверьте фильтр по Номенклатура_Key и ДокументОснование."
    if result.error_code == "FOREACH_ODATA_SOURCE_EMPTY":
        return "В заказе не найдена табличная часть Продукция или она пустая."
    return result.message or "Не удалось найти коды Честного знака через foreach OData."


def _friendly_foreach_validation_errors(errors: list[str]) -> list[str]:
    result: list[str] = []
    for error in errors:
        if "$top не может быть больше 500" in error or "$top должен быть" in error:
            result.append("$top не может быть больше 500. Поставьте 500 и включите пагинацию.")
        else:
            result.append(error)
    return result


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
        if root not in known and root != "request" and root != "context":
            result.append(f"В payload используется {variable}, но переменная {root} не создана. Проверьте Save as в предыдущих шагах.")
        else:
            result.append(f"В payload используется {variable}, но такого поля нет в данных шага. Проверьте $select и шаблон payload.")
    return result


def _friendly_final_action_errors(errors: list[str], payload_save_as: str) -> list[str]:
    result: list[str] = []
    for error in errors:
        if "target_payload" in error and payload_save_as != "target_payload":
            result.append(f"DnP endpoint отправляет target_payload, но payload сохранён как {payload_save_as}. Проверьте Payload Save as или Body source.")
        else:
            result.append(error)
    return result


def _foreach_warnings(top: int | None, paginate: bool) -> list[str]:
    if top == 500 and not paginate:
        return ["Для пула кодов обычно может быть больше 500 строк. Оставьте $top = 500 и включите пагинацию."]
    return []


def _codes_truncated_note(rows_found: int) -> str | None:
    if rows_found > 3:
        return f"codes: {rows_found} rows, showing first 3"
    return None


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


def _sample_number(contract: InputContract) -> str:
    request = _request_variable(contract)
    body = request.get("body") if isinstance(request, dict) else {}
    if isinstance(body, dict):
        value = body.get("Number") or body.get("order_name") or body.get("order_number")
        if value:
            return str(value)
    return "260666/6938"


