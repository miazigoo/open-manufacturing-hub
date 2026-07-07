from __future__ import annotations

import re
import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.odata_explorer import service as odata_explorer_service
from app.odata_explorer.schemas import ODataQueryRequest
from app.odata_connections import service as odata_connections_service
from app.integration_master.examples import scenario_by_key, scenarios
from app.integration_master.models import IntegrationMasterDraft
from app.integration_master.parser import parse_input
from app.integration_master.schemas import (
    BusinessKeySuggestion,
    InputContract,
    InputDraftRead,
    InputParseResponse,
    InputParseRequest,
    ODataFilterRule,
    ODataStepConfig,
    ODataStepPreviewResponse,
    ODataStepRequest,
    ODataStepTestResponse,
    ODataStepValidationResponse,
    OperationKeySuggestion,
)

SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,158}[a-z0-9])?$")
SAVE_AS_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
STEP_ID_PATTERN = re.compile(r"[^A-Za-z0-9_]+")
PLACEHOLDER_RE = re.compile(r"{{\s*([^}]+?)\s*}}")
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


def validate_odata_step(request: ODataStepRequest) -> ODataStepValidationResponse:
    context = _odata_step_context(request.input_contract, request.sample_input, request.odata_step)
    return ODataStepValidationResponse(
        valid=not context["errors"],
        errors=context["errors"],
        warnings=context["warnings"],
        template_filter=context["template_filter"],
        rendered_filter=context["rendered_filter"],
        template_url=context["template_url"],
        rendered_url=context["rendered_url"],
        variables_after_step=context["variables_after_step"],
    )


def preview_odata_step(request: ODataStepRequest) -> ODataStepPreviewResponse:
    context = _odata_step_context(request.input_contract, request.sample_input, request.odata_step)
    return ODataStepPreviewResponse(
        valid=not context["errors"],
        errors=context["errors"],
        warnings=context["warnings"],
        template_filter=context["template_filter"],
        rendered_filter=context["rendered_filter"],
        template_url=context["template_url"],
        rendered_url=context["rendered_url"],
        variables_after_step=context["variables_after_step"],
        rendered_resource=request.odata_step.resource.strip(),
        saved_as=request.odata_step.save_as.strip(),
    )


async def test_odata_step(session: AsyncSession, request: ODataStepRequest) -> ODataStepTestResponse:
    preview = preview_odata_step(request)
    if not preview.valid:
        return ODataStepTestResponse(
            success=False,
            error_code="ODATA_STEP_INVALID",
            message="; ".join(preview.errors),
            hint="Исправьте параметры OData-запроса и повторите проверку.",
            rendered_resource=preview.rendered_resource,
            rendered_filter=preview.rendered_filter,
            saved_as=preview.saved_as,
            variables_after_step=preview.variables_after_step,
        )
    connection_id = request.odata_step.connection_id
    if connection_id is None:
        return ODataStepTestResponse(success=False, error_code="ODATA_CONNECTION_REQUIRED", message="Выберите OData-подключение.", rendered_resource=preview.rendered_resource, rendered_filter=preview.rendered_filter, saved_as=preview.saved_as, variables_after_step=preview.variables_after_step)
    try:
        result = await odata_explorer_service.query(
            session,
            connection_id,
            ODataQueryRequest(
                resource=preview.rendered_resource,
                top=request.odata_step.top,
                filter=preview.rendered_filter,
                select=",".join(request.odata_step.select) if request.odata_step.select else None,
                orderby=request.odata_step.orderby or None,
                paginate=request.odata_step.paginate,
            ),
        )
    except BadRequestError as exc:
        return ODataStepTestResponse(
            success=False,
            error_code="ODATA_QUERY_FAILED",
            message=str(exc),
            hint="Проверьте подключение, resource, filter и права пользователя 1С.",
            rendered_resource=preview.rendered_resource,
            rendered_filter=preview.rendered_filter,
            saved_as=preview.saved_as,
            variables_after_step=preview.variables_after_step,
        )
    items = result.get("items") if isinstance(result.get("items"), list) else []
    if not items and request.odata_step.required:
        return ODataStepTestResponse(
            success=False,
            error_code="ODATA_RESULT_EMPTY",
            message=f"1C OData не вернула записей по фильтру {preview.rendered_filter}",
            hint="Проверьте номер заказа, ресурс OData и выбранное подключение.",
            rendered_resource=preview.rendered_resource,
            rendered_filter=preview.rendered_filter,
            items_count=0,
            saved_as=preview.saved_as,
            variables_after_step=preview.variables_after_step,
            request=result.get("request") if isinstance(result.get("request"), dict) else {},
        )
    first = items[0] if items and isinstance(items[0], dict) else None
    variables = _variables_after_step(request.odata_step, first)
    return ODataStepTestResponse(
        success=True,
        message=f"1С вернула {len(items)} записей",
        rendered_resource=preview.rendered_resource,
        rendered_filter=preview.rendered_filter,
        items_count=len(items),
        result_preview=first,
        saved_as=preview.saved_as,
        variables_after_step=variables,
        request=result.get("request") if isinstance(result.get("request"), dict) else {},
    )


async def append_odata_step(session: AsyncSession, draft_id: UUID, step: ODataStepConfig) -> tuple[InputDraftRead, ODataStepConfig]:
    draft = await session.get(IntegrationMasterDraft, draft_id)
    if draft is None:
        raise NotFoundError("Integration Master draft not found")
    contract = InputContract(**draft.contract_json)
    validation = validate_odata_step(ODataStepRequest(input_contract=contract, sample_input=contract.sample, odata_step=step))
    if not validation.valid:
        raise BadRequestError("; ".join(validation.errors))
    saved = _normalized_odata_step(step)
    if saved.connection_id and not saved.connection_name:
        try:
            connection = await odata_connections_service.get_connection(session, saved.connection_id)
            saved.connection_name = connection.name
        except NotFoundError:
            saved.connection_name = None
    existing_steps = [item for item in (draft.odata_steps_json or []) if isinstance(item, dict)]
    steps = [item for item in existing_steps if item.get("id") != saved.id]
    steps.append(saved.model_dump(mode="json"))
    draft.odata_steps_json = steps
    await session.flush()
    return _draft_read(draft), saved


def endpoint_url(slug: str) -> str:
    return f"/api/bus/in/{slug}"


def validate_slug(slug: str) -> None:
    if not SLUG_PATTERN.fullmatch(slug):
        raise BadRequestError("Endpoint slug должен содержать только lowercase letters, numbers, '-' и '_', без пробелов и спецсимволов.")


def _odata_step_context(contract: InputContract, sample_input: Any, step: ODataStepConfig) -> dict[str, Any]:
    errors = _validate_odata_step_fields(step)
    warnings: list[str] = []
    template_filter = _compile_step_filter(step)
    rendered_filter: str | None = None
    try:
        rendered_filter = _render_template(template_filter, contract, sample_input)
    except BadRequestError as exc:
        errors.append(str(exc))
    template_url = _odata_url(step.resource.strip(), template_filter, step)
    rendered_url = _odata_url(step.resource.strip(), rendered_filter, step)
    if step.paginate:
        warnings.append("Pagination сохранится в draft. Реальная многостраничная загрузка зависит от OData runtime.")
    return {
        "errors": errors,
        "warnings": warnings,
        "template_filter": template_filter,
        "rendered_filter": rendered_filter,
        "template_url": template_url,
        "rendered_url": rendered_url,
        "variables_after_step": _variables_after_step(step),
    }


def _validate_odata_step_fields(step: ODataStepConfig) -> list[str]:
    errors: list[str] = []
    if step.connection_id is None:
        errors.append("Выберите OData-подключение.")
    if not step.resource.strip():
        errors.append("Укажите Resource OData, например Document_ЗаказНаПроизводство2_2.")
    if step.top is None:
        errors.append("$top должен быть от 1 до 500.")
    elif step.top < 1 or step.top > 500:
        errors.append("$top должен быть от 1 до 500.")
    if not step.save_as.strip():
        errors.append("Укажите имя переменной, например order.")
    elif not SAVE_AS_PATTERN.fullmatch(step.save_as.strip()):
        errors.append("Имя переменной save_as должно содержать латиницу, цифры и underscore, и не начинаться с цифры.")
    if step.filter_mode == "builder" and step.filter_rule:
        if not step.filter_rule.field.strip():
            errors.append("Укажите поле OData для фильтра.")
        if step.filter_rule.value_type != "raw" and (step.filter_rule.value is None or step.filter_rule.value == ""):
            errors.append("Укажите значение фильтра.")
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


def _render_template(template: str | None, contract: InputContract, sample_input: Any) -> str | None:
    if not template:
        return None
    source = sample_input if sample_input is not None else contract.sample

    def replace(match: re.Match[str]) -> str:
        path = match.group(1).strip()
        value = _resolve_value(path, source, contract)
        return _escape_odata_string(str(value))

    return PLACEHOLDER_RE.sub(replace, template)


def _resolve_value(path: str, source: Any, contract: InputContract) -> Any:
    try:
        body = _json_source(source) if contract.input_mode == "json" else source
        if path.startswith("request.body."):
            return _get_nested(body, path.removeprefix("request.body."))
        if path == "request.raw_text":
            return str(source)
        if path.startswith("request.raw_text."):
            field = next((item for item in contract.fields if item.path == path), None)
            if field is not None:
                return field.example
        if path.startswith("xml."):
            field = next((item for item in contract.fields if item.path == path), None)
            if field is not None:
                return field.example
    except KeyError as exc:
        raise BadRequestError(f"Переменная {path} не найдена во входящем примере. Проверьте Input Contract.") from exc
    field = next((item for item in contract.fields if item.path == path), None)
    if field is not None and field.example is not None:
        return field.example
    raise BadRequestError(f"Переменная {path} не найдена во входящем примере. Проверьте Input Contract.")


def _json_source(source: Any) -> Any:
    if isinstance(source, str):
        try:
            return json.loads(source)
        except json.JSONDecodeError:
            return source
    return source


def _get_nested(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        raise KeyError(path)
    return current


def _odata_url(resource: str, filter_value: str | None, step: ODataStepConfig) -> str:
    if not resource:
        return ""
    params: list[str] = []
    if filter_value:
        params.append(f"$filter={filter_value}")
    if step.select:
        params.append(f"$select={','.join(step.select)}")
    if step.top:
        params.append(f"$top={step.top}")
    if step.orderby:
        params.append(f"$orderby={step.orderby}")
    if step.paginate:
        params.append("paginate=true")
    return resource if not params else f"{resource}?{'&'.join(params)}"


def _variables_after_step(step: ODataStepConfig, first_item: dict[str, Any] | None = None) -> list[str]:
    save_as = step.save_as.strip() or "result"
    fields = list(first_item.keys()) if first_item else list(step.select)
    if not fields:
        fields = ["Ref_Key", "Description"]
    return [f"{save_as}.{field}" for field in fields]


def _normalized_odata_step(step: ODataStepConfig) -> ODataStepConfig:
    save_as = step.save_as.strip()
    step_id = step.id or f"find_{save_as}"
    step_id = STEP_ID_PATTERN.sub("_", step_id).strip("_") or f"find_{save_as}"
    return step.model_copy(update={"id": step_id, "save_as": save_as, "filter": _compile_step_filter(step), "select": [item.strip() for item in step.select if item.strip()]})


def _escape_odata_string(value: str) -> str:
    return value.replace("'", "''")


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
    odata_steps = [ODataStepConfig(**item) for item in (draft.odata_steps_json or []) if isinstance(item, dict)]
    return InputDraftRead(
        id=draft.id,
        name=draft.name,
        slug=draft.slug,
        scenario_key=draft.scenario_key,
        input_mode=draft.input_mode,  # type: ignore[arg-type]
        source_system=draft.source_system,
        contract=contract,
        odata_steps=odata_steps,
        parse_result=parse_result,
        endpoint_url=endpoint_url(draft.slug),
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )
