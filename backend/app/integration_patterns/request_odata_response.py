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
    RequestODataResponseCreateResponse,
    RequestODataResponsePatternRequest,
    RequestODataResponsePreviewResponse,
    RequestODataResponseResponseConfig,
    RequestODataResponseRunTestRequest,
    RequestODataResponseRunTestResponse,
)


async def preview_pattern(session: AsyncSession, request: RequestODataResponsePatternRequest) -> RequestODataResponsePreviewResponse:
    contract = _contract(request)
    odata_step = request.odata_step
    payload_step = _payload_step(request.response)
    final_action = _final_action(request.response)

    input_validation = master_service.validate_input_contract(contract)
    odata_preview = master_service.preview_odata_step(ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=odata_step))
    odata_test = await master_service.test_odata_step(session, ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=odata_step))
    odata_result = odata_test.result_preview if odata_test.success else None
    previous_variables = _previous_variables(contract, odata_step.save_as, odata_result or _sample_odata_object(odata_step.select))

    payload_preview = master_service.preview_payload_step(PayloadStepRequest(input_contract=contract, previous_variables=previous_variables, payload_step=payload_step))
    variables_after_response = dict(previous_variables)
    if payload_preview.valid:
        variables_after_response[payload_step.save_as] = payload_preview.rendered_body
    final_preview = master_service.preview_final_action_step(FinalActionRequest(input_contract=contract, previous_variables=variables_after_response, final_action=final_action))

    errors = _dedupe(
        [
            *input_validation.get("errors", []),
            *([] if odata_preview.valid else odata_preview.errors),
            *([] if odata_test.success else [_friendly_odata_error(contract, odata_test)]),
            *_friendly_payload_errors(payload_preview.errors, odata_step.save_as),
            *final_preview.errors,
        ]
    )
    warnings = _dedupe([*odata_preview.warnings, *payload_preview.warnings, *final_preview.warnings])

    return RequestODataResponsePreviewResponse(
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
        response_to_caller=final_preview.caller_response_preview,
        human_steps=[
            f"receive POST {master_service.endpoint_url(contract.slug)}",
            "match operation key",
            f"odata_query {odata_step.save_as}",
            "build response",
            "return response",
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
            "variables_after_response": variables_after_response,
        },
    )


async def create_pattern(session: AsyncSession, request: RequestODataResponsePatternRequest) -> RequestODataResponseCreateResponse:
    contract = _contract(request)
    await _ensure_slug_available(session, contract.slug)
    preview = await preview_pattern(session, request)
    if not preview.valid:
        raise BadRequestError("; ".join(preview.errors))

    parse_result = master_service.parse_contract_input(InputParseRequest(input_mode=contract.input_mode, sample=contract.sample, scenario_key=contract.scenario_key))
    draft = await master_service.save_draft(session, contract, parse_result)
    draft, _ = await master_service.append_odata_step(session, draft.id, request.odata_step)

    previous_variables = preview.advanced.get("previous_variables")
    variables_after_response = preview.advanced.get("variables_after_response")
    if not isinstance(previous_variables, dict) or not isinstance(variables_after_response, dict):
        raise BadRequestError("Preview не вернул переменные для сохранения. Повторите preview и create.")

    draft, _ = await master_service.append_payload_step(session, draft.id, _payload_step(request.response), previous_variables)
    draft, _ = await master_service.save_final_action(session, draft.id, _final_action(request.response), variables_after_response)
    compiled = await master_service.compile_draft(
        session,
        draft.id,
        CompileDraftRequest(enabled=False, create_saved_test_case=True, comment="Created from Request -> OData -> Response wizard"),
    )
    return RequestODataResponseCreateResponse(draft_id=draft.id, compile=compiled, preview=preview)


async def run_test(session: AsyncSession, request: RequestODataResponseRunTestRequest) -> RequestODataResponseRunTestResponse:
    result = await master_service.run_compiled_test(session, request.integration_flow_id, CompiledRunTestRequest(dry_run=request.dry_run))
    return RequestODataResponseRunTestResponse(**result.model_dump())


def _contract(request: RequestODataResponsePatternRequest) -> InputContract:
    contract = request.input_contract
    return contract.model_copy(
        update={
            "name": request.name.strip(),
            "slug": request.slug.strip(),
            "scenario_key": contract.scenario_key or "external_contractor_lookup",
            "endpoint_url": master_service.endpoint_url(request.slug.strip()),
        }
    )


def _payload_step(response: RequestODataResponseResponseConfig) -> PayloadStepConfig:
    if response.type == "json":
        return PayloadStepConfig(
            type="build_payload",
            body_type="json",
            save_as="target_payload",
            json_mode="raw_template",
            template=response.body,
            fields=[],
            dynamic_entries=[],
            overwrite=True,
        )
    return PayloadStepConfig(
        type="build_payload",
        body_type=response.type,
        save_as="target_payload",
        json_mode="raw_template",
        template=_text_body(response.body),
        fields=[],
        dynamic_entries=[],
        overwrite=True,
    )


def _final_action(response: RequestODataResponseResponseConfig) -> FinalActionConfig:
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


def _previous_variables(contract: InputContract, save_as: str, odata_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "request": _request_variable(contract),
        "context": {"run_id": "preview-run-001", "event_id": "preview-event-001", "queue_item_id": "preview-queue-item-001"},
        save_as.strip() or "result": odata_result,
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
    fields = select_fields or ["Ref_Key", "Description"]
    sample: dict[str, Any] = {}
    for field in fields:
        if field.endswith("_Key") or field == "Ref_Key":
            sample[field] = "00000000-0000-0000-0000-000000000000"
        elif field.lower() in {"posted", "проведен"}:
            sample[field] = True
        elif field.lower() in {"date", "дата"}:
            sample[field] = "2026-07-12T12:00:00"
        else:
            sample[field] = f"sample_{field}"
    return sample


def _text_body(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


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


def _friendly_odata_error(contract: InputContract, result: ODataStepTestResponse) -> str:
    message = result.message or "OData query не прошёл проверку."
    if result.error_code == "ODATA_RESULT_EMPTY":
        value = _business_value(contract)
        label = "Контрагент" if "Контрагент" in result.rendered_resource else "Запись 1С"
        suffix = f" по ИНН {value}" if value else ""
        return (
            f"{label} не найден{suffix}. Проверьте: 1. Правильное OData-подключение. "
            "2. Есть ли запись в этой базе 1С. 3. Нет ли пробелов во входящем значении. "
            "4. Правильно ли называется поле OData."
        )
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
            result.append(f"В шаблоне ответа используется {variable}, но переменная {root} не создана. Проверьте имя Save as в OData-шаге.")
        else:
            result.append(f"В шаблоне ответа используется {variable}, но в результате {save_as} такого поля нет. Проверьте $select в OData-шаге.")
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
