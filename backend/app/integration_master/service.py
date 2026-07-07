from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.integration_master.examples import scenario_by_key, scenarios
from app.integration_master.models import IntegrationMasterDraft
from app.integration_master.parser import parse_input
from app.integration_master.schemas import (
    BusinessKeySuggestion,
    InputContract,
    InputDraftRead,
    InputParseResponse,
    InputParseRequest,
    OperationKeySuggestion,
)

SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,158}[a-z0-9])?$")
BUSINESS_KEY_PRIORITY = [
    "order_name",
    "number",
    "order_number",
    "inn",
    "wms_shipment_id",
    "job_key",
    "order_id",
    "printer",
    "sku",
    "номер",
    "инн",
]


def list_scenarios() -> list[dict[str, Any]]:
    return scenarios()


def parse_contract_input(request: InputParseRequest) -> InputParseResponse:
    parsed = parse_input(request.input_mode, request.sample)
    scenario = scenario_by_key(request.scenario_key)
    fields = parsed["fields"]
    return InputParseResponse(
        input_mode=request.input_mode,
        normalized_sample=parsed["normalized_sample"],
        fields=fields,
        suggested_operation_keys=_operation_key_suggestions(fields, scenario),
        suggested_business_keys=_business_key_suggestions(fields, scenario),
        warnings=parsed.get("warnings", []),
    )


def validate_input_contract(contract: InputContract) -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_slug(contract.slug)
    except BadRequestError as exc:
        errors.append(str(exc))
    field_paths = {field.path for field in contract.fields}
    if not contract.fields:
        errors.append("Input Contract должен содержать хотя бы одно поле. Для raw text используйте request.raw_text.")
    if contract.operation_key.type == "field" and contract.operation_key.field_path and contract.operation_key.field_path not in field_paths:
        errors.append(f"Route key path не найден среди полей: {contract.operation_key.field_path}")
    if contract.business_key.path and contract.business_key.path not in field_paths:
        errors.append(f"Business key path не найден среди полей: {contract.business_key.path}")
    matcher = operation_matcher(contract.operation_key)
    return {"valid": not errors, "errors": errors, "endpoint_url": endpoint_url(contract.slug), "matcher_preview": matcher}


async def save_draft(session: AsyncSession, contract: InputContract, parse_result: InputParseResponse | None) -> InputDraftRead:
    validation = validate_input_contract(contract)
    if not validation["valid"]:
        raise BadRequestError("; ".join(validation["errors"]))
    payload = contract.model_dump(mode="json")
    payload["endpoint_url"] = endpoint_url(contract.slug)
    draft = IntegrationMasterDraft(
        name=contract.name,
        slug=contract.slug,
        scenario_key=contract.scenario_key,
        input_mode=contract.input_mode,
        source_system=contract.source_system,
        contract_json=payload,
        parse_result_json=parse_result.model_dump(mode="json") if parse_result else None,
    )
    session.add(draft)
    await session.flush()
    return _draft_read(draft)


async def get_draft(session: AsyncSession, draft_id: UUID) -> InputDraftRead:
    draft = await session.get(IntegrationMasterDraft, draft_id)
    if draft is None:
        raise NotFoundError("Integration Master draft not found")
    return _draft_read(draft)


def endpoint_url(slug: str) -> str:
    return f"/api/bus/in/{slug}"


def validate_slug(slug: str) -> None:
    if not SLUG_PATTERN.fullmatch(slug):
        raise BadRequestError("Endpoint slug должен содержать только lowercase letters, numbers, '-' и '_', без пробелов и спецсимволов.")


def operation_matcher(operation_key: Any) -> dict[str, Any]:
    key_type = getattr(operation_key, "type", None) or (operation_key.get("type") if isinstance(operation_key, dict) else "field")
    if key_type == "none":
        return {"mode": "none", "rules": []}
    if key_type == "endpoint":
        return {"mode": "endpoint", "rules": []}
    field_path = getattr(operation_key, "field_path", None) or (operation_key.get("field_path") if isinstance(operation_key, dict) else None)
    value = getattr(operation_key, "value", None) if not isinstance(operation_key, dict) else operation_key.get("value")
    fallback_paths = getattr(operation_key, "fallback_paths", []) if not isinstance(operation_key, dict) else operation_key.get("fallback_paths", [])
    rules = []
    if field_path and value is not None:
        rules.append({"type": "body_path_equals", "path": _relative_matcher_path(field_path), "value": value})
    for fallback in fallback_paths or []:
        if value is not None:
            rules.append({"type": "body_path_equals", "path": _relative_matcher_path(fallback), "value": value})
    return {"mode": "any", "rules": rules}


def _operation_key_suggestions(fields: list[Any], scenario: dict[str, Any] | None) -> list[OperationKeySuggestion]:
    by_path = {field.path: field for field in fields}
    suggestions: list[OperationKeySuggestion] = []
    if scenario and scenario.get("recommended_operation_key"):
        rec = scenario["recommended_operation_key"]
        field = by_path.get(rec.get("field_path"))
        if field:
            suggestions.append(_operation_suggestion(field, rec.get("value", field.example), rec.get("fallback_paths") or []))
    candidates = sorted(
        [field for field in fields if field.type in {"string", "number", "boolean"} and _field_priority(field.name) is not None],
        key=lambda field: _field_priority(field.name) or 99,
    )
    for field in candidates:
        fallback_paths = []
        if field.name == "sinc":
            operation = next((item for item in fields if item.name == "operation" and item.example == field.example), None)
            if operation:
                fallback_paths.append(operation.path)
        suggestion = _operation_suggestion(field, field.example, fallback_paths)
        if suggestion.field_path not in {item.field_path for item in suggestions}:
            suggestions.append(suggestion)
    suggestions.append(OperationKeySuggestion(type="endpoint", label="По endpoint URL", human_text="OMH выберет сценарий по URL endpoint без проверки поля в body.", matcher_json={"mode": "endpoint", "rules": []}))
    suggestions.append(OperationKeySuggestion(type="none", label="Без ключа", human_text="Подходит только если endpoint используется для одного сценария.", matcher_json={"mode": "none", "rules": []}))
    return suggestions[:6]


def _business_key_suggestions(fields: list[Any], scenario: dict[str, Any] | None) -> list[BusinessKeySuggestion]:
    by_path = {field.path: field for field in fields}
    suggestions: list[BusinessKeySuggestion] = []
    if scenario and scenario.get("recommended_business_key"):
        rec = scenario["recommended_business_key"]
        field = by_path.get(rec.get("path"))
        if field:
            suggestions.append(BusinessKeySuggestion(path=field.path, field_name=field.name, fallback_paths=rec.get("fallback_paths") or [], label=f"{field.name}: {field.example}", example=field.example))
    scored = sorted(
        [field for field in fields if field.type in {"string", "number"}],
        key=lambda field: _business_priority(field.name),
    )
    for field in scored:
        if field.path in {item.path for item in suggestions}:
            continue
        fallback_paths = []
        if field.name in {"order_name", "order_number", "number", "Номер"}:
            fallback_paths = [item.path for item in fields if item.path != field.path and item.name in {"Number", "number", "order_number", "order_id", "Номер"}][:2]
        suggestions.append(BusinessKeySuggestion(path=field.path, field_name=field.name, fallback_paths=fallback_paths, label=f"{field.name}: {field.example}", example=field.example))
    return suggestions[:6]


def _operation_suggestion(field: Any, value: Any, fallback_paths: list[str]) -> OperationKeySuggestion:
    matcher = {"type": "field", "field_path": field.path, "value": value, "fallback_paths": fallback_paths}
    matcher_preview = operation_matcher(matcher)
    lines = [f"{_relative_matcher_path(field.path)} = {value}"] + [f"или {_relative_matcher_path(path)} = {value}" for path in fallback_paths]
    return OperationKeySuggestion(
        type="field",
        field_path=field.path,
        field_name=field.name,
        value=value,
        fallback_paths=fallback_paths,
        label=f"По полю {field.name}",
        human_text="OMH выберет этот сценарий, если: " + "; ".join(lines),
        matcher_json=matcher_preview,
    )


def _field_priority(name: str) -> int | None:
    lowered = name.lower()
    if lowered == "sinc":
        return 0
    if lowered == "operation":
        return 1
    if lowered in {"format", "тип"}:
        return 4
    return None


def _business_priority(name: str) -> int:
    lowered = name.lower()
    for index, candidate in enumerate(BUSINESS_KEY_PRIORITY):
        if lowered == candidate.lower():
            return index
    if "number" in lowered or "номер" in lowered:
        return 20
    if "id" in lowered or "key" in lowered:
        return 30
    return 80


def _relative_matcher_path(path: str) -> str:
    if path.startswith("request.body."):
        return path.removeprefix("request.body.")
    if path.startswith("request.raw_text."):
        return path.removeprefix("request.raw_text.")
    if path.startswith("xml."):
        return path.removeprefix("xml.")
    return path


def _draft_read(draft: IntegrationMasterDraft) -> InputDraftRead:
    contract = InputContract(**draft.contract_json)
    parse_result = InputParseResponse(**draft.parse_result_json) if draft.parse_result_json else None
    return InputDraftRead(
        id=draft.id,
        name=draft.name,
        slug=draft.slug,
        scenario_key=draft.scenario_key,
        input_mode=draft.input_mode,  # type: ignore[arg-type]
        source_system=draft.source_system,
        contract=contract,
        parse_result=parse_result,
        endpoint_url=endpoint_url(draft.slug),
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )
