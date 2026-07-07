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
    ForeachODataStepConfig,
    ForeachODataStepPreviewResponse,
    ForeachODataStepRequest,
    ForeachODataStepTestResponse,
    ForeachODataStepValidationResponse,
    InputContract,
    InputDraftRead,
    InputParseResponse,
    InputParseRequest,
    ODataFilterRule,
    ODataObjectStepConfig,
    ODataObjectStepPreviewResponse,
    ODataObjectStepRequest,
    ODataObjectStepTestResponse,
    ODataObjectStepValidationResponse,
    ResourceRenderResult,
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
GUID_PATTERN = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
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


def validate_odata_object_step(request: ODataObjectStepRequest) -> ODataObjectStepValidationResponse:
    context = _odata_object_step_context(request.previous_variables, request.odata_object_step)
    return ODataObjectStepValidationResponse(
        valid=not context["errors"],
        errors=context["errors"],
        warnings=context["warnings"],
        template_resource=context["template_resource"],
        rendered_resource=context["rendered_resource"],
        template_filter=context["template_filter"],
        rendered_filter=context["rendered_filter"],
        template_url=context["template_url"],
        rendered_url=context["rendered_url"],
        variables_after_step=context["variables_after_step"],
    )


def preview_odata_object_step(request: ODataObjectStepRequest) -> ODataObjectStepPreviewResponse:
    context = _odata_object_step_context(request.previous_variables, request.odata_object_step)
    return ODataObjectStepPreviewResponse(
        valid=not context["errors"],
        errors=context["errors"],
        warnings=context["warnings"],
        template_resource=context["template_resource"],
        rendered_resource=context["rendered_resource"],
        template_filter=context["template_filter"],
        rendered_filter=context["rendered_filter"],
        template_url=context["template_url"],
        rendered_url=context["rendered_url"],
        variables_after_step=context["variables_after_step"],
        saved_as=request.odata_object_step.save_as.strip(),
        object_variable=request.odata_object_step.object_variable.strip(),
        key_preview=context["key_preview"],
    )


async def test_odata_object_step(session: AsyncSession, request: ODataObjectStepRequest) -> ODataObjectStepTestResponse:
    preview = preview_odata_object_step(request)
    if not preview.valid:
        return ODataObjectStepTestResponse(
            success=False,
            error_code="ODATA_OBJECT_STEP_INVALID",
            message="; ".join(preview.errors),
            hint="Исправьте параметры чтения табличной части и повторите проверку.",
            rendered_resource=preview.rendered_resource or preview.template_resource or "",
            rendered_filter=preview.rendered_filter,
            saved_as=preview.saved_as,
            variables_after_step=preview.variables_after_step,
        )
    connection_id = request.odata_object_step.connection_id
    if connection_id is None:
        return ODataObjectStepTestResponse(
            success=False,
            error_code="ODATA_CONNECTION_REQUIRED",
            message="Выберите OData-подключение.",
            rendered_resource=preview.rendered_resource or "",
            rendered_filter=preview.rendered_filter,
            saved_as=preview.saved_as,
            variables_after_step=preview.variables_after_step,
        )
    try:
        result = await odata_explorer_service.query(
            session,
            connection_id,
            ODataQueryRequest(
                resource=preview.rendered_resource or "",
                top=request.odata_object_step.top,
                filter=preview.rendered_filter,
                select=",".join(request.odata_object_step.select) if request.odata_object_step.select else None,
                paginate=request.odata_object_step.paginate,
            ),
        )
    except BadRequestError as exc:
        return ODataObjectStepTestResponse(
            success=False,
            error_code="ODATA_TABULAR_PART_QUERY_FAILED",
            message=str(exc),
            hint="Проверьте resource, nested resource, Ref_Key и права пользователя 1С.",
            rendered_resource=preview.rendered_resource or "",
            rendered_filter=preview.rendered_filter,
            saved_as=preview.saved_as,
            variables_after_step=preview.variables_after_step,
        )
    items = result.get("items") if isinstance(result.get("items"), list) else []
    if not items and request.odata_object_step.required:
        return ODataObjectStepTestResponse(
            success=False,
            error_code="ODATA_TABULAR_PART_EMPTY",
            message=f"1C OData не вернула строк табличной части {request.odata_object_step.nested_resource.strip()}.",
            hint=f"Проверьте, что документ найден правильно и в нём есть строки {request.odata_object_step.nested_resource.strip()}.",
            rendered_resource=preview.rendered_resource or "",
            rendered_filter=preview.rendered_filter,
            items_count=0,
            saved_as=preview.saved_as,
            variables_after_step=preview.variables_after_step,
            request=result.get("request") if isinstance(result.get("request"), dict) else {},
        )
    preview_items = [item for item in items[:5] if isinstance(item, dict)]
    return ODataObjectStepTestResponse(
        success=True,
        message=f"1С вернула {len(items)} строк",
        rendered_resource=preview.rendered_resource or "",
        rendered_filter=preview.rendered_filter,
        items_count=len(items),
        result_preview=preview_items,
        saved_as=preview.saved_as,
        variables_after_step=_variables_after_object_step(request.odata_object_step, preview_items[0] if preview_items else None),
        request=result.get("request") if isinstance(result.get("request"), dict) else {},
    )


async def append_odata_object_step(session: AsyncSession, draft_id: UUID, step: ODataObjectStepConfig, previous_variables: dict[str, Any]) -> tuple[InputDraftRead, ODataObjectStepConfig]:
    draft = await session.get(IntegrationMasterDraft, draft_id)
    if draft is None:
        raise NotFoundError("Integration Master draft not found")
    contract = InputContract(**draft.contract_json)
    validation = validate_odata_object_step(ODataObjectStepRequest(input_contract=contract, previous_variables=previous_variables, odata_object_step=step))
    if not validation.valid:
        raise BadRequestError("; ".join(validation.errors))
    saved = _normalized_odata_object_step(step)
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


def validate_foreach_odata_step(request: ForeachODataStepRequest) -> ForeachODataStepValidationResponse:
    context = _foreach_odata_step_context(request.previous_variables, request.foreach_step)
    return ForeachODataStepValidationResponse(
        valid=not context["errors"],
        errors=context["errors"],
        warnings=context["warnings"],
        source_count=context["source_count"],
        first_item_preview=context["first_item_preview"],
        template_filter=context["template_filter"],
        rendered_filter=context["rendered_filter"],
        template_url=context["template_url"],
        rendered_url=context["rendered_url"],
        variables_after_step=context["variables_after_step"],
    )


def preview_foreach_odata_step(request: ForeachODataStepRequest) -> ForeachODataStepPreviewResponse:
    context = _foreach_odata_step_context(request.previous_variables, request.foreach_step)
    return ForeachODataStepPreviewResponse(
        valid=not context["errors"],
        errors=context["errors"],
        warnings=context["warnings"],
        source_count=context["source_count"],
        first_item_preview=context["first_item_preview"],
        template_filter=context["template_filter"],
        rendered_filter=context["rendered_filter"],
        template_url=context["template_url"],
        rendered_url=context["rendered_url"],
        variables_after_step=context["variables_after_step"],
        saved_as=request.foreach_step.save_as.strip(),
        items=request.foreach_step.items.strip(),
        item_as=request.foreach_step.item_as.strip(),
        merge=request.foreach_step.merge,
    )


async def test_foreach_odata_step(session: AsyncSession, request: ForeachODataStepRequest) -> ForeachODataStepTestResponse:
    preview = preview_foreach_odata_step(request)
    step = request.foreach_step
    if not preview.valid:
        return ForeachODataStepTestResponse(
            success=False,
            error_code="FOREACH_ODATA_STEP_INVALID",
            message="; ".join(preview.errors),
            hint="Исправьте параметры foreach OData и повторите проверку.",
            source_count=preview.source_count,
            merge=step.merge,
            saved_as=preview.saved_as,
            variables_after_step=preview.variables_after_step,
        )
    if step.connection_id is None:
        return ForeachODataStepTestResponse(
            success=False,
            error_code="ODATA_CONNECTION_REQUIRED",
            message="Выберите OData-подключение.",
            source_count=preview.source_count,
            merge=step.merge,
            saved_as=preview.saved_as,
            variables_after_step=preview.variables_after_step,
        )

    source_items = _source_array(request.previous_variables, step.items.strip())
    if not source_items:
        if step.required:
            return ForeachODataStepTestResponse(
                success=False,
                error_code="FOREACH_ODATA_SOURCE_EMPTY",
                message=f"Массив {step.items.strip()} пуст. Нечего передавать во вложенный OData-запрос.",
                hint="Сначала протестируйте предыдущий шаг чтения табличной части и убедитесь, что он вернул products[].",
                source_count=0,
                merge=step.merge,
                saved_as=preview.saved_as,
                variables_after_step=preview.variables_after_step,
            )
        source_items = []

    items_to_process = _limit_foreach_items_for_test(source_items, step)
    if len(items_to_process) > step.limits.max_requests:
        return ForeachODataStepTestResponse(
            success=False,
            error_code="FOREACH_ODATA_REQUEST_LIMIT_EXCEEDED",
            message=f"Для теста нужно {len(items_to_process)} OData-запросов, но max_requests={step.limits.max_requests}.",
            hint="Уменьшите test_limit или увеличьте safety limit.",
            source_count=len(source_items),
            merge=step.merge,
            saved_as=preview.saved_as,
            variables_after_step=preview.variables_after_step,
        )

    grouped_rows: list[dict[str, Any]] = []
    requests: list[dict[str, Any]] = []
    rows_found = 0
    for index, item in enumerate(items_to_process):
        if not isinstance(item, dict):
            return ForeachODataStepTestResponse(
                success=False,
                error_code="FOREACH_ODATA_ITEM_NOT_OBJECT",
                message=f"Элемент {step.items.strip()}[{index}] не является объектом. Нельзя прочитать поля через {step.item_as.strip()}.field.",
                hint="Источник foreach должен быть массивом строк/объектов, например products[].",
                source_count=len(source_items),
                items_processed=index,
                odata_requests=len(requests),
                rows_found=rows_found,
                merge=step.merge,
                saved_as=preview.saved_as,
                variables_after_step=preview.variables_after_step,
                requests=requests,
            )
        local_variables = {**request.previous_variables, step.item_as.strip(): item}
        try:
            rendered_resource = _render_previous_template(step.resource.strip(), local_variables) or ""
            rendered_filter = _render_previous_template((step.filter or "").strip() or None, local_variables)
        except BadRequestError as exc:
            return ForeachODataStepTestResponse(
                success=False,
                error_code="FOREACH_ODATA_TEMPLATE_FAILED",
                message=str(exc),
                hint=f"Проверьте поля элемента {step.item_as.strip()} и переменные предыдущих шагов.",
                source_count=len(source_items),
                items_processed=index,
                odata_requests=len(requests),
                rows_found=rows_found,
                merge=step.merge,
                saved_as=preview.saved_as,
                variables_after_step=preview.variables_after_step,
                requests=requests,
            )
        try:
            result = await odata_explorer_service.query(
                session,
                step.connection_id,
                ODataQueryRequest(
                    resource=rendered_resource,
                    top=step.top,
                    filter=rendered_filter,
                    select=",".join(step.select) if step.select else None,
                    paginate=step.paginate,
                ),
            )
        except BadRequestError as exc:
            return ForeachODataStepTestResponse(
                success=False,
                error_code="FOREACH_ODATA_QUERY_FAILED",
                message=str(exc),
                hint=f"Проверьте resource/filter для элемента {step.items.strip()}[{index}] и права пользователя 1С.",
                source_count=len(source_items),
                items_processed=index,
                odata_requests=len(requests),
                rows_found=rows_found,
                merge=step.merge,
                saved_as=preview.saved_as,
                variables_after_step=preview.variables_after_step,
                requests=requests,
            )
        rows = [row for row in (result.get("items") if isinstance(result.get("items"), list) else []) if isinstance(row, dict)]
        rows_found += len(rows)
        request_payload = result.get("request") if isinstance(result.get("request"), dict) else {}
        requests.append({"item_index": index, "resource": rendered_resource, "filter": rendered_filter, "request": request_payload})
        grouped_rows.append({"item_index": index, "item": item, "rows": rows})
        if rows_found > step.limits.max_result_rows:
            return ForeachODataStepTestResponse(
                success=False,
                error_code="FOREACH_ODATA_RESULT_LIMIT_EXCEEDED",
                message=f"Результат превысил max_result_rows={step.limits.max_result_rows}. Сейчас найдено {rows_found} строк.",
                hint="Уточните фильтр, уменьшите top или увеличьте safety limit осознанно.",
                source_count=len(source_items),
                items_processed=index + 1,
                odata_requests=len(requests),
                rows_found=rows_found,
                merge=step.merge,
                saved_as=preview.saved_as,
                variables_after_step=preview.variables_after_step,
                requests=requests,
            )

    if rows_found == 0 and step.required:
        return ForeachODataStepTestResponse(
            success=False,
            error_code="FOREACH_ODATA_RESULT_EMPTY",
            message=f"1C OData не вернула строк по массиву {step.items.strip()}.",
            hint="Проверьте фильтр, Номенклатура_Key из products[] и order.Ref_Key.",
            source_count=len(source_items),
            items_processed=len(items_to_process),
            odata_requests=len(requests),
            rows_found=0,
            merge=step.merge,
            saved_as=preview.saved_as,
            variables_after_step=preview.variables_after_step,
            requests=requests,
        )

    merged = _merge_foreach_rows(grouped_rows, step.merge)
    first_row = _first_foreach_row(grouped_rows)
    return ForeachODataStepTestResponse(
        success=True,
        message=f"Выполнено {len(requests)} OData-запросов, найдено {rows_found} строк.",
        source_count=len(source_items),
        items_processed=len(items_to_process),
        odata_requests=len(requests),
        rows_found=rows_found,
        merge=step.merge,
        saved_as=preview.saved_as,
        result_preview=_preview_foreach_result(merged, step.merge),
        variables_after_step=_variables_after_foreach_step(step, first_row),
        requests=requests,
    )


async def append_foreach_odata_step(session: AsyncSession, draft_id: UUID, step: ForeachODataStepConfig, previous_variables: dict[str, Any]) -> tuple[InputDraftRead, ForeachODataStepConfig]:
    draft = await session.get(IntegrationMasterDraft, draft_id)
    if draft is None:
        raise NotFoundError("Integration Master draft not found")
    contract = InputContract(**draft.contract_json)
    validation = validate_foreach_odata_step(ForeachODataStepRequest(input_contract=contract, previous_variables=previous_variables, foreach_step=step))
    if not validation.valid:
        raise BadRequestError("; ".join(validation.errors))
    saved = _normalized_foreach_odata_step(step)
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


def render_1c_object_resource(base_resource: str, key_template: str, key_type: str, nested_resource: str, variables: dict[str, Any]) -> ResourceRenderResult:
    template_key = _object_key_expression(_normalize_placeholder(key_template), key_type)
    template_resource = f"{base_resource.strip()}({template_key})/{nested_resource.strip().strip('/')}"
    try:
        rendered_resource = _render_previous_template(template_resource, variables)
    except BadRequestError:
        rendered_resource = None
    return ResourceRenderResult(template_resource=template_resource, rendered_resource=rendered_resource)


def _odata_object_step_context(previous_variables: dict[str, Any], step: ODataObjectStepConfig) -> dict[str, Any]:
    errors = _validate_odata_object_step_fields(step, previous_variables)
    warnings: list[str] = []
    object_variable = step.object_variable.strip()
    key_field = step.key_field.strip() or "Ref_Key"
    key_template = f"{{{{{object_variable}.{key_field}}}}}" if object_variable else "{{object.Ref_Key}}"
    render = render_1c_object_resource(step.base_resource, key_template, step.key_type, step.nested_resource, previous_variables)
    rendered_resource = render.rendered_resource
    key_preview = _object_key_preview(previous_variables, object_variable, key_field)
    if step.key_type == "guid" and rendered_resource and key_preview is not None and not GUID_PATTERN.fullmatch(str(key_preview)):
        errors.append(f"Значение {object_variable}.{key_field} не похоже на GUID. Проверьте, что предыдущий шаг вернул правильный Ref_Key.")
    template_filter = (step.filter or "").strip() or None
    rendered_filter: str | None = None
    try:
        rendered_filter = _render_previous_template(template_filter, previous_variables)
    except BadRequestError as exc:
        errors.append(str(exc))
    template_url = _odata_object_url(render.template_resource, template_filter, step)
    rendered_url = _odata_object_url(rendered_resource, rendered_filter, step)
    if step.paginate:
        warnings.append("Pagination сохранится в draft. Runtime будет читать следующие страницы через $skip.")
    return {
        "errors": _dedupe_errors(errors),
        "warnings": warnings,
        "template_resource": render.template_resource,
        "rendered_resource": rendered_resource,
        "template_filter": template_filter,
        "rendered_filter": rendered_filter,
        "template_url": template_url,
        "rendered_url": rendered_url,
        "variables_after_step": _variables_after_object_step(step),
        "key_preview": key_preview,
    }


def _validate_odata_object_step_fields(step: ODataObjectStepConfig, previous_variables: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if step.connection_id is None:
        errors.append("Выберите OData-подключение.")
    object_variable = step.object_variable.strip()
    key_field = step.key_field.strip() or "Ref_Key"
    if not object_variable:
        errors.append("Выберите объект, у которого нужно прочитать табличную часть.")
    elif object_variable not in previous_variables:
        errors.append(f"Переменная {object_variable} не найдена среди результатов предыдущих шагов.")
    else:
        value = previous_variables[object_variable]
        if isinstance(value, list):
            errors.append(f"Переменная {object_variable} является массивом. Для массива используйте шаг \"Повторить OData по массиву\", он будет следующим этапом.")
        elif not isinstance(value, dict):
            errors.append(f"Переменная {object_variable} должна быть объектом 1С.")
        elif key_field not in value:
            errors.append(f"В переменной {object_variable} нет поля {key_field}. Проверьте Select предыдущего OData-запроса. Нужно получить {key_field}.")
        elif step.key_type == "guid" and not GUID_PATTERN.fullmatch(str(value.get(key_field) or "")):
            errors.append(f"Значение {object_variable}.{key_field} не похоже на GUID. Проверьте, что предыдущий шаг вернул правильный Ref_Key.")
    if not step.base_resource.strip():
        errors.append("Укажите базовый OData Resource, например Document_ЗаказНаПроизводство2_2.")
    if not step.nested_resource.strip():
        errors.append("Укажите табличную часть / вложенный ресурс, например Продукция.")
    if step.top is None:
        errors.append("$top должен быть от 1 до 500.")
    elif step.top < 1 or step.top > 500:
        errors.append("$top должен быть от 1 до 500.")
    if not step.save_as.strip():
        errors.append("Укажите имя массива, например products.")
    elif not SAVE_AS_PATTERN.fullmatch(step.save_as.strip()):
        errors.append("Имя переменной save_as должно содержать латиницу, цифры и underscore, и не начинаться с цифры.")
    elif step.save_as.strip() in previous_variables and not step.overwrite:
        errors.append(f"Переменная {step.save_as.strip()} уже существует. Выберите другое имя или подтвердите overwrite.")
    return _dedupe_errors(errors)


def _foreach_odata_step_context(previous_variables: dict[str, Any], step: ForeachODataStepConfig) -> dict[str, Any]:
    errors = _validate_foreach_odata_step_fields(step, previous_variables)
    warnings: list[str] = []
    source_items = _source_array(previous_variables, step.items.strip())
    first_item = next((item for item in source_items if isinstance(item, dict)), None)
    if source_items and first_item is None:
        errors.append(f"Массив {step.items.strip()} должен содержать объекты, например строки products[].")
    template_filter = (step.filter or "").strip() or None
    template_resource = step.resource.strip()
    rendered_filter: str | None = None
    rendered_resource: str | None = None
    if first_item is not None:
        local_variables = {**previous_variables, step.item_as.strip(): first_item}
        try:
            rendered_filter = _render_previous_template(template_filter, local_variables)
            rendered_resource = _render_previous_template(template_resource, local_variables)
        except BadRequestError as exc:
            errors.append(str(exc))
    elif template_resource:
        rendered_resource = template_resource
    template_url = _odata_foreach_url(template_resource, template_filter, step)
    rendered_url = _odata_foreach_url(rendered_resource, rendered_filter, step)
    if step.paginate:
        warnings.append("Pagination включён: для каждой строки массива OMH будет читать следующие страницы через $skip.")
    if template_filter and f"{{{{{step.item_as.strip()}." not in template_filter:
        warnings.append(f"Фильтр не использует {step.item_as.strip()}.*. Такой запрос повторится одинаково для каждой строки массива.")
    if not source_items and step.items.strip() in previous_variables:
        warnings.append(f"Массив {step.items.strip()} пуст в текущем sample. Test не выполнит вложенные OData-запросы.")
    return {
        "errors": _dedupe_errors(errors),
        "warnings": warnings,
        "source_count": len(source_items),
        "first_item_preview": first_item,
        "template_filter": template_filter,
        "rendered_filter": rendered_filter,
        "template_url": template_url,
        "rendered_url": rendered_url,
        "variables_after_step": _variables_after_foreach_step(step),
    }


def _validate_foreach_odata_step_fields(step: ForeachODataStepConfig, previous_variables: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if step.connection_id is None:
        errors.append("Выберите OData-подключение.")
    items_name = step.items.strip()
    if not items_name:
        errors.append("Выберите массив, по которому нужно пройти, например products.")
    elif items_name not in previous_variables:
        errors.append(f"Переменная {items_name} не найдена среди результатов предыдущих шагов.")
    elif not isinstance(previous_variables[items_name], list):
        errors.append(f"Переменная {items_name} является {_value_type_ru(previous_variables[items_name])}, а не массивом. Для объекта используйте обычный OData-запрос или чтение табличной части.")
    else:
        source_count = len(previous_variables[items_name])
        if source_count > step.limits.max_items:
            errors.append(f"Массив {items_name} содержит {source_count} строк, но max_items={step.limits.max_items}.")
        if source_count > step.limits.max_requests:
            errors.append(f"Для массива {items_name} потребуется {source_count} OData-запросов, но max_requests={step.limits.max_requests}.")
    item_as = step.item_as.strip()
    if not item_as:
        errors.append("Укажите имя одной строки массива, например product.")
    elif not SAVE_AS_PATTERN.fullmatch(item_as):
        errors.append("Имя item_as должно содержать латиницу, цифры и underscore, и не начинаться с цифры.")
    elif item_as in previous_variables:
        errors.append(f"Имя item_as={item_as} конфликтует с переменной предыдущего шага. Выберите другое имя.")
    if not step.resource.strip():
        errors.append("Укажите OData Resource для вложенного запроса, например InformationRegister_ПулКодовМаркировкиСУЗ.")
    if not (step.filter or "").strip():
        errors.append("Укажите $filter для вложенного OData-запроса. Без фильтра foreach может прочитать слишком много строк.")
    if step.top is None:
        errors.append("$top должен быть от 1 до 500.")
    elif step.top < 1 or step.top > 500:
        errors.append("$top не может быть больше 500. Установите 500 и включите пагинацию.")
    if not step.save_as.strip():
        errors.append("Укажите имя общего массива результата, например codes.")
    elif not SAVE_AS_PATTERN.fullmatch(step.save_as.strip()):
        errors.append("Имя переменной save_as должно содержать латиницу, цифры и underscore, и не начинаться с цифры.")
    elif step.save_as.strip() in previous_variables and not step.overwrite:
        errors.append(f"Переменная {step.save_as.strip()} уже существует. Выберите другое имя или подтвердите overwrite.")
    if step.limits.max_items < 1:
        errors.append("max_items должен быть больше 0.")
    if step.limits.max_requests < 1:
        errors.append("max_requests должен быть больше 0.")
    if step.limits.max_result_rows < 1:
        errors.append("max_result_rows должен быть больше 0.")
    if step.test_limit is not None and step.test_limit < 1:
        errors.append("test_limit должен быть больше 0 или null для проверки всего массива.")
    return _dedupe_errors(errors)


def _source_array(previous_variables: dict[str, Any], name: str) -> list[Any]:
    value = previous_variables.get(name)
    return value if isinstance(value, list) else []


def _limit_foreach_items_for_test(source_items: list[Any], step: ForeachODataStepConfig) -> list[Any]:
    if step.test_limit is None:
        return source_items[: step.limits.max_items]
    return source_items[: min(step.test_limit, step.limits.max_items)]


def _value_type_ru(value: Any) -> str:
    if isinstance(value, dict):
        return "объектом"
    if isinstance(value, list):
        return "массивом"
    if isinstance(value, str):
        return "строкой"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "числом"
    return type(value).__name__


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


def _render_previous_template(template: str | None, variables: dict[str, Any]) -> str | None:
    if not template:
        return None

    def replace(match: re.Match[str]) -> str:
        path = match.group(1).strip()
        value = _resolve_previous_value(path, variables)
        return _escape_odata_string(str(value))

    return PLACEHOLDER_RE.sub(replace, template)


def _resolve_previous_value(path: str, variables: dict[str, Any]) -> Any:
    root, _, tail = path.partition(".")
    if not root or root not in variables:
        raise BadRequestError(f"Переменная {path} не найдена среди результатов предыдущих шагов.")
    value = variables[root]
    if not tail:
        return value
    try:
        return _get_nested(value, tail)
    except KeyError as exc:
        raise BadRequestError(f"Переменная {path} не найдена среди результатов предыдущих шагов.") from exc


def _object_key_preview(variables: dict[str, Any], object_variable: str, key_field: str) -> Any:
    value = variables.get(object_variable)
    if isinstance(value, dict):
        return value.get(key_field)
    return None


def _normalize_placeholder(value: str) -> str:
    placeholder = value.strip()
    if not placeholder.startswith("{{"):
        placeholder = "{{" + placeholder + "}}"
    return placeholder


def _object_key_expression(key_template: str, key_type: str) -> str:
    if key_type == "guid":
        return f"guid'{key_template}'"
    if key_type == "string":
        return f"'{key_template}'"
    return key_template


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


def _odata_object_url(resource: str | None, filter_value: str | None, step: ODataObjectStepConfig) -> str | None:
    if not resource:
        return None
    params: list[str] = []
    if filter_value:
        params.append(f"$filter={filter_value}")
    if step.select:
        params.append(f"$select={','.join(step.select)}")
    if step.top:
        params.append(f"$top={step.top}")
    if step.paginate:
        params.append("paginate=true")
    return resource if not params else f"{resource}?{'&'.join(params)}"


def _odata_foreach_url(resource: str | None, filter_value: str | None, step: ForeachODataStepConfig) -> str | None:
    if not resource:
        return None
    params: list[str] = []
    if filter_value:
        params.append(f"$filter={filter_value}")
    if step.select:
        params.append(f"$select={','.join(step.select)}")
    if step.top:
        params.append(f"$top={step.top}")
    if step.paginate:
        params.append("paginate=true")
    return resource if not params else f"{resource}?{'&'.join(params)}"


def _variables_after_step(step: ODataStepConfig, first_item: dict[str, Any] | None = None) -> list[str]:
    save_as = step.save_as.strip() or "result"
    fields = list(first_item.keys()) if first_item else list(step.select)
    if not fields:
        fields = ["Ref_Key", "Description"]
    return [f"{save_as}.{field}" for field in fields]


def _variables_after_object_step(step: ODataObjectStepConfig, first_item: dict[str, Any] | None = None) -> list[str]:
    save_as = step.save_as.strip() or "items"
    fields = list(first_item.keys()) if first_item else list(step.select)
    if not fields:
        fields = ["Номенклатура_Key", "Количество"]
    return [f"{save_as}[]"] + [f"{save_as}[0].{field}" for field in fields]


def _variables_after_foreach_step(step: ForeachODataStepConfig, first_item: dict[str, Any] | None = None) -> list[str]:
    save_as = step.save_as.strip() or "items"
    fields = list(first_item.keys()) if first_item else list(step.select)
    if not fields:
        fields = ["КодМаркировки", "Номенклатура_Key"]
    return [f"{save_as}[]"] + [f"{save_as}[0].{field}" for field in fields]


def _normalized_odata_step(step: ODataStepConfig) -> ODataStepConfig:
    save_as = step.save_as.strip()
    step_id = step.id or f"find_{save_as}"
    step_id = STEP_ID_PATTERN.sub("_", step_id).strip("_") or f"find_{save_as}"
    return step.model_copy(update={"id": step_id, "save_as": save_as, "filter": _compile_step_filter(step), "select": [item.strip() for item in step.select if item.strip()]})


def _normalized_odata_object_step(step: ODataObjectStepConfig) -> ODataObjectStepConfig:
    save_as = step.save_as.strip()
    step_id = step.id or f"read_{save_as}"
    step_id = STEP_ID_PATTERN.sub("_", step_id).strip("_") or f"read_{save_as}"
    key_template = f"{{{{{step.object_variable.strip()}.{(step.key_field.strip() or 'Ref_Key')}}}}}"
    template = render_1c_object_resource(step.base_resource, key_template, step.key_type, step.nested_resource, {}).template_resource
    return step.model_copy(
        update={
            "id": step_id,
            "save_as": save_as,
            "key_field": step.key_field.strip() or "Ref_Key",
            "base_resource": step.base_resource.strip(),
            "nested_resource": step.nested_resource.strip().strip("/"),
            "resource_template": template,
            "filter": (step.filter or "").strip() or None,
            "select": [item.strip() for item in step.select if item.strip()],
        }
    )


def _normalized_foreach_odata_step(step: ForeachODataStepConfig) -> ForeachODataStepConfig:
    save_as = step.save_as.strip()
    step_id = step.id or f"find_{save_as}"
    step_id = STEP_ID_PATTERN.sub("_", step_id).strip("_") or f"find_{save_as}"
    return step.model_copy(
        update={
            "id": step_id,
            "items": step.items.strip(),
            "item_as": step.item_as.strip(),
            "resource": step.resource.strip(),
            "filter": (step.filter or "").strip() or None,
            "select": [item.strip() for item in step.select if item.strip()],
            "save_as": save_as,
        }
    )


def _merge_foreach_rows(grouped_rows: list[dict[str, Any]], merge: str) -> Any:
    if merge == "group_by_item":
        return grouped_rows
    if merge == "first_per_item":
        return [group["rows"][0] for group in grouped_rows if isinstance(group.get("rows"), list) and group["rows"]]
    merged: list[dict[str, Any]] = []
    for group in grouped_rows:
        rows = group.get("rows")
        if isinstance(rows, list):
            merged.extend([row for row in rows if isinstance(row, dict)])
    return merged


def _preview_foreach_result(merged: Any, merge: str) -> Any:
    if isinstance(merged, list):
        return merged[:5]
    return merged


def _first_foreach_row(grouped_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    for group in grouped_rows:
        rows = group.get("rows")
        if isinstance(rows, list):
            first = next((row for row in rows if isinstance(row, dict)), None)
            if first is not None:
                return first
    return None


def _step_read(item: dict[str, Any]) -> ODataStepConfig | ODataObjectStepConfig | ForeachODataStepConfig:
    if item.get("type") == "foreach_odata":
        return ForeachODataStepConfig(**item)
    if item.get("type") == "odata_object_query":
        return ODataObjectStepConfig(**item)
    return ODataStepConfig(**item)


def _dedupe_errors(errors: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for error in errors:
        if error not in seen:
            seen.add(error)
            result.append(error)
    return result


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
    odata_steps = [_step_read(item) for item in (draft.odata_steps_json or []) if isinstance(item, dict)]
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
