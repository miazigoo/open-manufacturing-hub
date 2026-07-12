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
    ODataStepRequest,
    ODataStepTestResponse,
    PayloadStepConfig,
    PayloadStepRequest,
)
from app.integration_patterns.schemas import (
    RequestODataSendEndpointCreateResponse,
    RequestODataSendEndpointPatternRequest,
    RequestODataSendEndpointPreviewResponse,
    RequestODataSendEndpointResponseConfig,
    RequestODataSendEndpointRunTestRequest,
    RequestODataSendEndpointRunTestResponse,
    RequestODataSendEndpointTargetConfig,
)


async def preview_pattern(session: AsyncSession, request: RequestODataSendEndpointPatternRequest) -> RequestODataSendEndpointPreviewResponse:
    contract = _contract(request)
    odata_step = request.odata_step
    payload_step = _payload_step(request.payload)
    final_action = _final_action(request.target, request.response_to_caller)

    input_validation = master_service.validate_input_contract(contract)
    odata_preview = master_service.preview_odata_step(ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=odata_step))
    odata_test = await master_service.test_odata_step(session, ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=odata_step))
    odata_result = odata_test.result_preview if odata_test.success else None
    previous_variables = _previous_variables(contract, odata_step.save_as, odata_result or _sample_odata_object(odata_step.select))

    payload_preview = master_service.preview_payload_step(PayloadStepRequest(input_contract=contract, previous_variables=previous_variables, payload_step=payload_step))
    variables_after_payload = dict(previous_variables)
    if payload_preview.valid:
        variables_after_payload[payload_step.save_as] = payload_preview.rendered_body
    final_preview = master_service.preview_final_action_step(FinalActionRequest(input_contract=contract, previous_variables=variables_after_payload, final_action=final_action))

    errors = _dedupe(
        [
            *input_validation.get("errors", []),
            *([] if odata_preview.valid else odata_preview.errors),
            *([] if odata_test.success else [_friendly_odata_error(contract, odata_test)]),
            *_friendly_payload_errors(payload_preview.errors, odata_step.save_as),
            *_friendly_final_action_errors(final_preview.errors, payload_step.save_as),
        ]
    )
    warnings = _dedupe([*odata_preview.warnings, *payload_preview.warnings, *final_preview.warnings])

    return RequestODataSendEndpointPreviewResponse(
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
        target_payload=payload_preview.rendered_body if payload_preview.valid else None,
        target_request=final_preview.send_preview,
        response_to_caller=final_preview.caller_response_preview,
        human_steps=[
            f"receive POST {master_service.endpoint_url(contract.slug)}",
            "match operation key",
            f"odata_query {odata_step.save_as}",
            f"build payload {payload_step.save_as}",
            f"send {final_action.method} {final_action.url}",
            _caller_step_label(request.response_to_caller),
        ],
        advanced={
            "input_contract_validation": input_validation,
            "odata_preview": odata_preview.model_dump(mode="json"),
            "odata_test": odata_test.model_dump(mode="json"),
            "payload_step": payload_step.model_dump(mode="json"),
            "payload_preview": payload_preview.model_dump(mode="json"),
            "final_action": final_action.model_dump(mode="json"),
            "final_preview": final_preview.model_dump(mode="json"),
            "previous_variables": previous_variables,
            "variables_after_payload": variables_after_payload,
        },
    )


async def create_pattern(session: AsyncSession, request: RequestODataSendEndpointPatternRequest) -> RequestODataSendEndpointCreateResponse:
    contract = _contract(request)
    await _ensure_slug_available(session, contract.slug)
    preview = await preview_pattern(session, request)
    if not preview.valid:
        raise BadRequestError("; ".join(preview.errors))

    parse_result = master_service.parse_contract_input(InputParseRequest(input_mode=contract.input_mode, sample=contract.sample, scenario_key=contract.scenario_key))
    draft = await master_service.save_draft(session, contract, parse_result)
    draft, _ = await master_service.append_odata_step(session, draft.id, request.odata_step)

    previous_variables = preview.advanced.get("previous_variables")
    variables_after_payload = preview.advanced.get("variables_after_payload")
    if not isinstance(previous_variables, dict) or not isinstance(variables_after_payload, dict):
        raise BadRequestError("Preview не вернул переменные для сохранения. Повторите preview и create.")

    draft, _ = await master_service.append_payload_step(session, draft.id, _payload_step(request.payload), previous_variables)
    draft, _ = await master_service.save_final_action(session, draft.id, _final_action(request.target, request.response_to_caller), variables_after_payload)
    compiled = await master_service.compile_draft(
        session,
        draft.id,
        CompileDraftRequest(enabled=False, create_saved_test_case=True, comment="Created from Request -> OData -> Send Endpoint wizard"),
    )
    return RequestODataSendEndpointCreateResponse(draft_id=draft.id, compile=compiled, preview=preview)


async def run_test(session: AsyncSession, request: RequestODataSendEndpointRunTestRequest) -> RequestODataSendEndpointRunTestResponse:
    result = await master_service.run_compiled_test(session, request.integration_flow_id, CompiledRunTestRequest(dry_run=request.dry_run))
    return RequestODataSendEndpointRunTestResponse(**result.model_dump())


def _contract(request: RequestODataSendEndpointPatternRequest) -> InputContract:
    contract = request.input_contract
    return contract.model_copy(
        update={
            "name": request.name.strip(),
            "slug": request.slug.strip(),
            "scenario_key": contract.scenario_key or "onec_publish_order_to_site",
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


def _previous_variables(contract: InputContract, save_as: str, odata_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "request": _request_variable(contract),
        "context": {"run_id": "preview-run-001", "event_id": "preview-event-001", "queue_item_id": "preview-queue-item-001"},
        save_as.strip() or "order": odata_result,
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


def _sample_odata_object(select_fields: list[str]) -> dict[str, Any]:
    fields = select_fields or ["Ref_Key", "Number", "Date", "Posted"]
    sample: dict[str, Any] = {}
    for field in fields:
        lower = field.lower()
        if field.endswith("_Key") or field == "Ref_Key":
            sample[field] = "00000000-0000-0000-0000-000000000000"
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
    message = result.message or "OData query не прошёл проверку."
    if result.error_code == "ODATA_RESULT_EMPTY":
        value = _business_value(contract)
        resource = result.rendered_resource or ""
        if "Заказ" in resource or "Order" in resource:
            suffix = f" по номеру {value}" if value else ""
            return f"Заказ не найден{suffix}. Проверьте OData-подключение, ресурс и номер заказа."
        suffix = f" по ключу {value}" if value else ""
        return f"Запись 1С не найдена{suffix}. Проверьте OData-подключение, ресурс и входящий ключ."
    if result.error_code == "ODATA_QUERY_FAILED" and re.search(r"\b(401|403|unauthorized|forbidden)\b", message, re.I):
        return "1С не приняла логин или пароль. Проверьте OData-подключение."
    return message


def _business_value(contract: InputContract) -> str | None:
    path = contract.business_key.path
    if not path or not path.startswith("request.body."):
        return None
    source = contract.sample
    if isinstance(source, str):
        try:
            source = json.loads(source)
        except json.JSONDecodeError:
            return None
    if not isinstance(source, dict):
        return None
    value: Any = source
    for part in path.removeprefix("request.body.").split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return str(value)


def _friendly_payload_errors(errors: list[str], save_as: str) -> list[str]:
    result: list[str] = []
    for error in errors:
        match = re.search(r"Переменная\s+([^ ]+)\s+не найдена", error)
        if not match:
            result.append(error)
            continue
        variable = match.group(1)
        root = variable.split(".", 1)[0]
        if root != save_as:
            result.append(f"В payload используется {variable}, но переменная {root} не создана. Проверьте Save as в OData-шаге.")
        else:
            result.append(f"В payload используется {variable}, но в результате {save_as} такого поля нет. Проверьте $select в OData-шаге.")
    return result


def _friendly_final_action_errors(errors: list[str], payload_save_as: str) -> list[str]:
    result: list[str] = []
    for error in errors:
        if "target_payload" in error and payload_save_as != "target_payload":
            result.append(f"Target endpoint отправляет target_payload, но payload сохранён как {payload_save_as}. Проверьте Payload Save as или Body source.")
        elif "Endpoint не ответил" in error:
            result.append("Внешний endpoint не ответил за заданное время. Увеличьте timeout или проверьте сеть.")
        else:
            result.append(error)
    return result


def _caller_step_label(response: RequestODataSendEndpointResponseConfig) -> str:
    if response.type == "proxy_response":
        return "return target endpoint response"
    if response.type == "accepted_event":
        return "return accepted event"
    return "return configured caller response"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
