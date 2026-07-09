from __future__ import annotations

import re
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import repository as connector_repository
from app.core.errors import BadRequestError, NotFoundError
from app.flow_builder.validator import validate_builder
from app.integration_bus import repository as bus_repository
from app.integration_bus.models import IntegrationEndpoint, IntegrationRoute
from app.integration_flows import repository as flow_repository
from app.integration_flows import service as integration_flows_service
from app.integration_flows.models import IntegrationFlow
from app.integration_master.compiler import CompileIssue as CompilerIssue, compile_master_draft
from app.odata_explorer import service as odata_explorer_service
from app.odata_explorer.schemas import ODataQueryRequest
from app.odata_connections import service as odata_connections_service
from app.integration_master.examples import scenario_by_key, scenarios
from app.integration_master.final_action import (
    preview_final_action as preview_final_action_config,
    test_final_action as test_final_action_config,
    validate_final_action as validate_final_action_config,
)
from app.integration_master.models import IntegrationMasterDraft
from app.integration_master.payload_renderer import PayloadRenderError, render_payload_step
from app.integration_master.parser import parse_input
from app.integration_master.schemas import (
    BusinessKeySuggestion,
    CompileDraftRequest,
    CompileDraftResponse,
    CompileDraftValidationResponse,
    CompileIssue,
    CompilePreviewResponse,
    CompiledEnableResponse,
    CompiledRunTestRequest,
    CompiledRunTestResponse,
    FinalActionConfig,
    FinalActionPreviewResponse,
    FinalActionRequest,
    FinalActionTestRequest,
    FinalActionTestResponse,
    FinalActionValidationResponse,
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
    PayloadStepConfig,
    PayloadStepPreviewResponse,
    PayloadStepRequest,
    PayloadStepValidationResponse,
)
from app.test_console import service as test_console_service
from app.test_console.models import SavedTestCase
from app.workflows.models import Workflow

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
    unique_slug = await _unique_draft_slug(session, contract.slug)
    if unique_slug != contract.slug:
        contract = contract.model_copy(update={"slug": unique_slug, "endpoint_url": endpoint_url(unique_slug)})
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


async def validate_draft_for_compile(session: AsyncSession, draft_id: UUID) -> CompileDraftValidationResponse:
    draft = await _draft_for_compile(session, draft_id)
    errors, warnings = await _compile_issues(session, draft)
    if not errors:
        compiled = compile_master_draft(draft)
        if not compiled.builder_json:
            errors.append(CompilerIssue("builder_json", None, "Не удалось собрать builder_json. Проверьте шаги мастера."))
        else:
            validation = validate_builder(compiled.builder_json)
            for item in validation.get("errors", []):
                errors.append(CompilerIssue("builder_json", str(item.get("step_id") or ""), str(item.get("message") or item.get("code"))))
            for item in validation.get("warnings", []):
                warnings.append(CompilerIssue("builder_json", str(item.get("step_id") or ""), str(item.get("message") or item.get("code"))))
    return CompileDraftValidationResponse(valid=not errors, errors=_issue_schema(errors), warnings=_issue_schema(warnings))


async def preview_compile_draft(session: AsyncSession, draft_id: UUID) -> CompilePreviewResponse:
    draft = await _draft_for_compile(session, draft_id)
    validation = await validate_draft_for_compile(session, draft_id)
    advanced: dict[str, Any] = {}
    will_create: dict[str, Any] = {}
    if validation.valid:
        compiled = compile_master_draft(draft)
        will_create = compiled.will_create
        advanced = {
            "builder_json": compiled.builder_json,
            "workflow_steps": compiled.workflow_steps,
            "flow_payload": compiled.flow_payload.model_dump(mode="json"),
        }
    return CompilePreviewResponse(valid=validation.valid, errors=validation.errors, warnings=validation.warnings, will_create=will_create, advanced=advanced)


async def compile_draft(session: AsyncSession, draft_id: UUID, request: CompileDraftRequest) -> CompileDraftResponse:
    draft = await _draft_for_compile(session, draft_id)
    validation = await validate_draft_for_compile(session, draft_id)
    if not validation.valid:
        raise BadRequestError("; ".join(issue.message for issue in validation.errors))
    await _ensure_slug_available(session, draft)
    compiled = compile_master_draft(draft, enabled=request.enabled, create_saved_test_case=request.create_saved_test_case, comment=request.comment)
    flow = await integration_flows_service.create_flow(session, compiled.flow_payload)
    endpoint = await session.get(IntegrationEndpoint, flow.endpoint_id) if flow.endpoint_id else None
    route = await session.get(IntegrationRoute, flow.route_id) if flow.route_id else None
    if endpoint is None or route is None:
        raise BadRequestError("Compiled integration was created without endpoint or route. Transaction rolled back.")
    test_case = await _test_case_for_flow(session, flow)
    if test_case is not None and not request.create_saved_test_case:
        await session.delete(test_case)
        test_case = None
        await session.flush()
    return CompileDraftResponse(
        success=True,
        integration_flow_id=flow.id,
        endpoint_id=endpoint.id,
        route_id=route.id,
        saved_test_case_id=test_case.id if test_case else None,
        enabled=flow.enabled,
        endpoint={"method": "POST", "url": endpoint_url(flow.slug)},
        curl_example=integration_flows_service.curl_example(flow.slug, endpoint.input_mode, flow.test_payload_text or flow.test_payload_json),
        onec_http_example=integration_flows_service.onec_http_example(flow.slug, endpoint.input_mode),
        next_actions=[
            "Отправьте тестовый запрос из сохраненного test case.",
            "Откройте Timeline и проверьте шаги OData, payload и final action.",
            "Если все работает, включите интеграцию.",
        ],
    )


async def run_compiled_test(session: AsyncSession, integration_flow_id: UUID, request: CompiledRunTestRequest) -> CompiledRunTestResponse:
    flow = await integration_flows_service.get_flow_or_404(session, integration_flow_id)
    test_case = await _test_case_for_flow(session, flow)
    if test_case is None:
        raise NotFoundError("Saved test case for compiled integration not found")
    result = await test_console_service.run_test_case(session, test_case.id, dry_run=request.dry_run)
    event_id = result.get("event_id")
    return CompiledRunTestResponse(
        success=bool(result.get("success")),
        dry_run=bool(result.get("dry_run")),
        saved_test_case_id=test_case.id,
        response=result,
        event_id=event_id,
        timeline_url=result.get("timeline_url") or (f"/events/{event_id}" if event_id else None),
    )


async def enable_compiled_integration(session: AsyncSession, integration_flow_id: UUID) -> CompiledEnableResponse:
    flow = await integration_flows_service.get_flow_or_404(session, integration_flow_id)
    flow.enabled = True
    endpoint_enabled = False
    route_enabled = False
    workflow_enabled = False
    if flow.endpoint_id:
        endpoint = await session.get(IntegrationEndpoint, flow.endpoint_id)
        if endpoint:
            endpoint.enabled = True
            endpoint_enabled = True
    if flow.route_id:
        route = await session.get(IntegrationRoute, flow.route_id)
        if route:
            route.enabled = True
            route_enabled = True
    if flow.workflow_id:
        workflow = await session.get(Workflow, flow.workflow_id)
        if workflow:
            workflow.enabled = True
            workflow_enabled = True
    await session.flush()
    return CompiledEnableResponse(success=True, integration_flow_id=flow.id, enabled=flow.enabled, endpoint_enabled=endpoint_enabled, route_enabled=route_enabled, workflow_enabled=workflow_enabled)


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
        result_body=merged,
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


def validate_payload_step(request: PayloadStepRequest) -> PayloadStepValidationResponse:
    context = _payload_step_context(request.previous_variables, request.payload_step)
    return PayloadStepValidationResponse(
        valid=not context["errors"],
        errors=context["errors"],
        warnings=context["warnings"],
        body_type=request.payload_step.body_type,
        save_as=request.payload_step.save_as.strip(),
        variables_after_step=context["variables_after_step"],
        error_code=context["error_code"],
    )


def preview_payload_step(request: PayloadStepRequest) -> PayloadStepPreviewResponse:
    context = _payload_step_context(request.previous_variables, request.payload_step)
    return PayloadStepPreviewResponse(
        valid=not context["errors"],
        errors=context["errors"],
        warnings=context["warnings"],
        body_type=request.payload_step.body_type,
        save_as=request.payload_step.save_as.strip(),
        variables_after_step=context["variables_after_step"],
        error_code=context["error_code"],
        rendered_body=context["rendered_body"],
        rendered_preview=context["rendered_preview"],
        size_bytes=context["size_bytes"],
    )


async def append_payload_step(session: AsyncSession, draft_id: UUID, step: PayloadStepConfig, previous_variables: dict[str, Any]) -> tuple[InputDraftRead, PayloadStepConfig]:
    draft = await session.get(IntegrationMasterDraft, draft_id)
    if draft is None:
        raise NotFoundError("Integration Master draft not found")
    validation = validate_payload_step(PayloadStepRequest(input_contract=InputContract(**draft.contract_json), previous_variables=previous_variables, payload_step=step))
    if not validation.valid:
        raise BadRequestError("; ".join(validation.errors))
    saved = _normalized_payload_step(step)
    existing_steps = [item for item in (draft.odata_steps_json or []) if isinstance(item, dict)]
    steps = [item for item in existing_steps if item.get("id") != saved.id]
    steps.append(saved.model_dump(mode="json"))
    draft.odata_steps_json = steps
    await session.flush()
    return _draft_read(draft), saved


def validate_final_action_step(request: FinalActionRequest) -> FinalActionValidationResponse:
    validation = validate_final_action_config(request.final_action, request.previous_variables)
    return FinalActionValidationResponse(
        valid=validation.valid,
        errors=validation.errors,
        warnings=validation.warnings,
        action_type=request.final_action.type,
        error_code=validation.error_code,
    )


def preview_final_action_step(request: FinalActionRequest) -> FinalActionPreviewResponse:
    preview = preview_final_action_config(request.final_action, request.previous_variables)
    return FinalActionPreviewResponse(
        valid=preview.success,
        success=preview.success,
        errors=preview.errors,
        warnings=preview.warnings,
        action_type=request.final_action.type,
        error_code=preview.error_code,
        send_preview=preview.send_preview,
        caller_response_preview=preview.caller_response_preview,
        human_preview=preview.human_preview,
    )


async def test_final_action_step(request: FinalActionTestRequest) -> FinalActionTestResponse:
    result = await test_final_action_config(request.final_action, request.previous_variables, dry_run=request.dry_run)
    return FinalActionTestResponse(
        success=result.success,
        dry_run=result.dry_run,
        error_code=result.error_code,
        message=result.message,
        would_send=result.would_send,
        would_return_to_caller=result.would_return_to_caller,
        target_status=result.target_status,
        target_response=result.target_response,
        caller_response=result.caller_response,
    )


async def save_final_action(session: AsyncSession, draft_id: UUID, final_action: FinalActionConfig, previous_variables: dict[str, Any]) -> tuple[InputDraftRead, FinalActionConfig]:
    draft = await session.get(IntegrationMasterDraft, draft_id)
    if draft is None:
        raise NotFoundError("Integration Master draft not found")
    validation = validate_final_action_config(final_action, previous_variables)
    if not validation.valid:
        raise BadRequestError("; ".join(validation.errors))
    saved = _normalized_final_action(final_action)
    draft.final_action_json = saved.model_dump(mode="json")
    await session.flush()
    return _draft_read(draft), saved


async def _draft_for_compile(session: AsyncSession, draft_id: UUID) -> InputDraftRead:
    draft = await get_draft(session, draft_id)
    enriched_steps: list[ODataStepConfig | ODataObjectStepConfig | ForeachODataStepConfig | PayloadStepConfig] = []
    for step in draft.odata_steps:
        if isinstance(step, (ODataStepConfig, ODataObjectStepConfig, ForeachODataStepConfig)) and step.connection_id and not step.connection_name:
            try:
                connection = await odata_connections_service.get_connection(session, step.connection_id)
                enriched_steps.append(step.model_copy(update={"connection_name": connection.name}))
                continue
            except NotFoundError:
                pass
        enriched_steps.append(step)
    return draft.model_copy(update={"odata_steps": enriched_steps})


async def _compile_issues(session: AsyncSession, draft: InputDraftRead) -> tuple[list[CompilerIssue], list[CompilerIssue]]:
    errors: list[CompilerIssue] = []
    warnings: list[CompilerIssue] = []
    contract = draft.contract
    field_paths = {field.path for field in contract.fields}
    if not contract.name.strip():
        errors.append(CompilerIssue("input_contract", "name", "Укажите название интеграции."))
    if not contract.slug.strip():
        errors.append(CompilerIssue("input_contract", "slug", "Укажите endpoint slug."))
    else:
        try:
            validate_slug(contract.slug)
        except BadRequestError as exc:
            errors.append(CompilerIssue("input_contract", "slug", str(exc)))
    if contract.input_mode not in {"json", "xml", "raw_text"}:
        errors.append(CompilerIssue("input_contract", "input_mode", "Поддерживаются только JSON, XML и raw text."))
    if contract.sample in (None, "", {}, []):
        errors.append(CompilerIssue("input_contract", "sample", "Input Contract должен содержать sample request."))
    if contract.operation_key.type == "field":
        if not contract.operation_key.field_path:
            errors.append(CompilerIssue("input_contract", "operation_key", "Operation key настроен как field, но путь не указан."))
        elif contract.operation_key.field_path not in field_paths:
            errors.append(CompilerIssue("input_contract", "operation_key", f"Operation key path не найден в Input Contract: {contract.operation_key.field_path}"))
        if contract.operation_key.value in (None, ""):
            errors.append(CompilerIssue("input_contract", "operation_key", "Operation key value пустой."))
    if contract.business_key.path and contract.business_key.path not in field_paths:
        fallback_known = any(path in field_paths for path in contract.business_key.fallback_paths)
        if not fallback_known:
            errors.append(CompilerIssue("input_contract", "business_key", f"Business key path не найден в Input Contract: {contract.business_key.path}"))
    elif not contract.business_key.path:
        warnings.append(CompilerIssue("input_contract", "business_key", "Business key не выбран. Timeline будет сложнее искать оператору."))

    variables = _initial_compile_variables(draft)
    seen_variables = set(variables)
    payload_step_seen = False
    for step in draft.odata_steps:
        if isinstance(step, ODataStepConfig):
            await _validate_compile_odata_step(session, step, "odata_query", errors)
            _check_save_as(step.save_as, "odata_query", seen_variables, errors)
            variables[step.save_as] = _sample_object(step.select)
            seen_variables.add(step.save_as)
        elif isinstance(step, ODataObjectStepConfig):
            await _validate_compile_odata_object_step(session, step, variables, errors)
            _check_save_as(step.save_as, "odata_object_query", seen_variables, errors)
            variables[step.save_as] = [_sample_object(step.select)]
            seen_variables.add(step.save_as)
        elif isinstance(step, ForeachODataStepConfig):
            await _validate_compile_foreach_step(session, step, variables, errors, warnings)
            _check_save_as(step.save_as, "foreach_odata", seen_variables, errors)
            variables[step.save_as] = [_sample_object(step.select)]
            seen_variables.add(step.save_as)
        elif isinstance(step, PayloadStepConfig):
            payload_step_seen = True
            _validate_compile_payload_step(step, variables, errors, warnings)
            _check_save_as(step.save_as, "payload", seen_variables, errors)
            variables[step.save_as] = {} if step.body_type == "json" else ""
            seen_variables.add(step.save_as)

    if draft.final_action is None:
        errors.append(CompilerIssue("final_action", None, "Сохраните финальное действие перед созданием интеграции."))
    else:
        if draft.final_action.body_source == "target_payload" and "target_payload" not in variables:
            errors.append(CompilerIssue("final_action", "body_source", "Финальное действие использует target_payload, но payload step его не создал."))
        validation = validate_final_action_config(draft.final_action, variables)
        for message in validation.errors:
            errors.append(CompilerIssue("final_action", validation.error_code, message))
        for message in validation.warnings:
            warnings.append(CompilerIssue("final_action", validation.error_code, message))
    if not payload_step_seen:
        warnings.append(CompilerIssue("payload", None, "Payload step не найден. Это допустимо только для сценариев без target_payload."))
    return errors, warnings


async def _validate_compile_odata_step(session: AsyncSession, step: ODataStepConfig, section: str, errors: list[CompilerIssue]) -> None:
    await _check_compile_connection(session, step, section, errors)
    if not step.resource.strip():
        errors.append(CompilerIssue(section, "resource", "Укажите OData resource."))
    _check_top(section, step.top, errors)
    if not step.save_as.strip():
        errors.append(CompilerIssue(section, "save_as", "Укажите имя переменной результата."))


async def _validate_compile_odata_object_step(session: AsyncSession, step: ODataObjectStepConfig, variables: dict[str, Any], errors: list[CompilerIssue]) -> None:
    section = "odata_object_query"
    await _check_compile_connection(session, step, section, errors)
    if not step.object_variable.strip() or step.object_variable.strip() not in variables:
        errors.append(CompilerIssue(section, "object_variable", f"Переменная {step.object_variable or '<empty>'} не найдена. Сначала сохраните OData step, который создаёт объект."))
    if not step.base_resource.strip():
        errors.append(CompilerIssue(section, "base_resource", "Укажите базовый resource документа 1C."))
    if not step.nested_resource.strip():
        errors.append(CompilerIssue(section, "nested_resource", "Укажите табличную часть документа 1C."))
    _check_top(section, step.top, errors)


async def _validate_compile_foreach_step(session: AsyncSession, step: ForeachODataStepConfig, variables: dict[str, Any], errors: list[CompilerIssue], warnings: list[CompilerIssue]) -> None:
    section = "foreach_odata"
    await _check_compile_connection(session, step, section, errors)
    if not step.items.strip() or step.items.strip() not in variables:
        errors.append(CompilerIssue(section, "items", f"Массив {step.items or '<empty>'} не найден. Сначала сохраните шаг, который создаёт массив."))
    elif not isinstance(variables.get(step.items.strip()), list):
        errors.append(CompilerIssue(section, "items", f"Переменная {step.items} должна быть массивом."))
    if not step.resource.strip():
        errors.append(CompilerIssue(section, "resource", "Укажите OData resource для вложенного запроса."))
    if not (step.filter or "").strip():
        errors.append(CompilerIssue(section, "filter", "Укажите $filter для foreach OData."))
    _check_top(section, step.top, errors)
    if step.top == 500 and step.paginate:
        warnings.append(CompilerIssue(section, "top", "$top = 500. Для больших результатов включена пагинация."))


def _validate_compile_payload_step(step: PayloadStepConfig, variables: dict[str, Any], errors: list[CompilerIssue], warnings: list[CompilerIssue]) -> None:
    section = "payload"
    if not step.save_as.strip():
        errors.append(CompilerIssue(section, "save_as", "Укажите имя payload-переменной."))
    if step.body_type not in {"json", "xml", "raw_text"}:
        errors.append(CompilerIssue(section, "body_type", "Выберите формат payload: JSON, XML или raw text."))
    if step.body_type == "json" and step.json_mode == "table" and not step.fields and not step.dynamic_entries:
        errors.append(CompilerIssue(section, "fields", "Добавьте хотя бы одно JSON поле или dynamic entry."))
    if step.body_type == "json" and step.json_mode == "raw_template" and step.template in (None, ""):
        errors.append(CompilerIssue(section, "template", "Укажите raw JSON template."))
    if step.body_type in {"xml", "raw_text"} and step.template in (None, ""):
        errors.append(CompilerIssue(section, "template", "Укажите template для XML/raw payload."))
    unknown_roots = sorted(_unknown_placeholder_roots(step, variables))
    for root in unknown_roots:
        warnings.append(CompilerIssue(section, "template", f"Payload template ссылается на {root}, но в compile preview нет sample-значения. Проверьте Dry Run после создания."))


async def _check_compile_connection(session: AsyncSession, step: Any, section: str, errors: list[CompilerIssue]) -> None:
    if not getattr(step, "connection_id", None):
        connection_name = str(getattr(step, "connection_name", "") or "").strip()
        if connection_name and await connector_repository.get_by_name(session, connection_name):
            return
        errors.append(CompilerIssue(section, "connection_id", "Выберите OData-подключение."))
        return
    try:
        await odata_connections_service.get_connection(session, step.connection_id)
    except NotFoundError:
        errors.append(CompilerIssue(section, "connection_id", f"OData-подключение не найдено: {step.connection_id}"))


def _check_top(section: str, top: int | None, errors: list[CompilerIssue]) -> None:
    if top is None or top < 1 or top > 500:
        errors.append(CompilerIssue(section, "top", "$top должен быть от 1 до 500."))


def _check_save_as(save_as: str, section: str, seen_variables: set[str], errors: list[CompilerIssue]) -> None:
    value = save_as.strip()
    if not value:
        errors.append(CompilerIssue(section, "save_as", "Укажите имя переменной результата."))
    elif not SAVE_AS_PATTERN.fullmatch(value):
        errors.append(CompilerIssue(section, "save_as", "Имя переменной save_as должно содержать латиницу, цифры и underscore, и не начинаться с цифры."))
    elif value in seen_variables:
        errors.append(CompilerIssue(section, "save_as", f"Переменная {value} уже существует. Выберите другое имя."))


def _initial_compile_variables(draft: InputDraftRead) -> dict[str, Any]:
    sample = draft.contract.sample
    if draft.input_mode == "json":
        body = sample if isinstance(sample, dict) else {}
        request = {"body": body}
    elif draft.input_mode == "xml":
        request = {"body": {}, "xml": str(sample or "")}
    else:
        request = {"body": {}, "raw_text": str(sample or "")}
    return {
        "request": request,
        "context": {"run_id": "preview-run", "event_id": "preview-event", "queue_item_id": "preview-queue"},
    }


def _sample_object(select_fields: list[str]) -> dict[str, Any]:
    fields = select_fields or ["Ref_Key", "Description"]
    sample: dict[str, Any] = {}
    for field in fields:
        if field.endswith("_Key") or field == "Ref_Key" or "Основание" in field:
            sample[field] = "00000000-0000-0000-0000-000000000000"
        elif "Количество" in field:
            sample[field] = 1
        else:
            sample[field] = f"sample_{field}"
    return sample


def _unknown_placeholder_roots(step: PayloadStepConfig, variables: dict[str, Any]) -> set[str]:
    roots: set[str] = set()
    payload = step.model_dump(mode="json")
    text = json.dumps(payload, ensure_ascii=False)
    for match in PLACEHOLDER_RE.finditer(text):
        expression = match.group(1).strip()
        root = re.split(r"[.\\[]", expression, maxsplit=1)[0]
        if root and root not in variables and root not in {"variables", "steps"}:
            roots.add(root)
    return roots


async def _ensure_slug_available(session: AsyncSession, draft: InputDraftRead) -> None:
    flow_name = f"{draft.name} [{draft.slug}]"
    endpoint_name = f"Flow {flow_name} Endpoint"
    if await bus_repository.get_endpoint_by_slug(session, draft.slug) or await bus_repository.get_endpoint_by_name(session, endpoint_name):
        raise BadRequestError(f"Endpoint {endpoint_url(draft.slug)} уже существует. Выберите другой slug.")
    if await flow_repository.get_by_slug(session, draft.slug):
        raise BadRequestError(f"Integration Flow со slug {draft.slug} уже существует. Выберите другой slug.")
    existing_flow_by_name = await session.execute(select(IntegrationFlow).where(IntegrationFlow.name == flow_name))
    if existing_flow_by_name.scalar_one_or_none() is not None:
        raise BadRequestError(f"Integration Flow с названием {flow_name} уже существует. Измените название или slug.")


async def _unique_draft_slug(session: AsyncSession, requested_slug: str) -> str:
    validate_slug(requested_slug)
    base = requested_slug[:160].strip("_-") or "integration"
    candidate = base
    suffix = 2
    while await _slug_is_taken(session, candidate):
        suffix_text = f"-{suffix}"
        candidate = f"{base[:160 - len(suffix_text)].rstrip('_-')}{suffix_text}"
        suffix += 1
    return candidate


async def _slug_is_taken(session: AsyncSession, slug: str) -> bool:
    draft_result = await session.execute(select(IntegrationMasterDraft.id).where(IntegrationMasterDraft.slug == slug).limit(1))
    if draft_result.scalar_one_or_none() is not None:
        return True
    if await bus_repository.get_endpoint_by_slug(session, slug):
        return True
    return await flow_repository.get_by_slug(session, slug) is not None


async def _test_case_for_flow(session: AsyncSession, flow: IntegrationFlow) -> SavedTestCase | None:
    if not flow.endpoint_id:
        return None
    result = await session.execute(select(SavedTestCase).where(SavedTestCase.endpoint_id == flow.endpoint_id).order_by(SavedTestCase.updated_at.desc()))
    return result.scalars().first()


def _issue_schema(issues: list[CompilerIssue]) -> list[CompileIssue]:
    return [CompileIssue(section=issue.section, field=issue.field, message=issue.message) for issue in issues]


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


def _payload_step_context(previous_variables: dict[str, Any], step: PayloadStepConfig) -> dict[str, Any]:
    errors = _validate_payload_step_fields(step, previous_variables)
    warnings: list[str] = []
    rendered_body: Any = None
    rendered_preview: Any = None
    size_bytes = 0
    error_code: str | None = None
    try:
        result = render_payload_step(step, previous_variables)
        rendered_body = result.rendered_body
        rendered_preview = result.rendered_preview
        size_bytes = result.size_bytes
        warnings.extend(result.warnings)
    except PayloadRenderError as exc:
        errors.append(exc.message)
        error_code = exc.code
    return {
        "errors": _dedupe_errors(errors),
        "warnings": _dedupe_errors(warnings),
        "rendered_body": rendered_body,
        "rendered_preview": rendered_preview,
        "size_bytes": size_bytes,
        "variables_after_step": _variables_after_payload_step(step),
        "error_code": error_code,
    }


def _validate_payload_step_fields(step: PayloadStepConfig, previous_variables: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    save_as = step.save_as.strip()
    if not save_as:
        errors.append("Укажите имя переменной результата, например target_payload.")
    elif not SAVE_AS_PATTERN.fullmatch(save_as):
        errors.append("Имя переменной save_as должно содержать латиницу, цифры и underscore, и не начинаться с цифры.")
    elif save_as in previous_variables and not step.overwrite:
        errors.append(f"Переменная {save_as} уже существует. Выберите другое имя или подтвердите overwrite.")

    if step.body_type == "json":
        if step.json_mode == "table" and not step.fields and not step.dynamic_entries:
            errors.append("Добавьте хотя бы одно поле JSON или dynamic object entry.")
        if step.json_mode == "raw_template" and not step.template:
            errors.append("Укажите raw JSON template.")
    elif step.body_type in {"xml", "raw_text"}:
        if not step.template:
            errors.append("Укажите template для body.")
    else:
        errors.append("Выберите формат тела: JSON, XML или raw text.")
    return _dedupe_errors(errors)


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
        fields = ["ПолныйКодМаркировки", "ДокументОснование", "Номенклатура_Key"]
    return [f"{save_as}[]"] + [f"{save_as}[0].{field}" for field in fields]


def _variables_after_payload_step(step: PayloadStepConfig) -> list[str]:
    return [step.save_as.strip() or "target_payload"]


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


def _normalized_payload_step(step: PayloadStepConfig) -> PayloadStepConfig:
    save_as = step.save_as.strip()
    step_id = step.id or f"build_{save_as}"
    step_id = STEP_ID_PATTERN.sub("_", step_id).strip("_") or f"build_{save_as}"
    return step.model_copy(
        update={
            "id": step_id,
            "save_as": save_as,
            "fields": [field.model_copy(update={"target_path": field.target_path.strip()}) for field in step.fields if field.target_path.strip()],
            "dynamic_entries": [
                entry.model_copy(update={"object_path": entry.object_path.strip(), "key_source": entry.key_source.strip()})
                for entry in step.dynamic_entries
                if entry.object_path.strip() and entry.key_source.strip()
            ],
            "last_preview_status": "success",
        }
    )


def _normalized_final_action(final_action: FinalActionConfig) -> FinalActionConfig:
    return_to_caller = final_action.return_to_caller
    if final_action.type == "send_and_return_response":
        return_to_caller = return_to_caller.model_copy(update={"type": "proxy_response"})
    return final_action.model_copy(
        update={
            "url": (final_action.url or "").strip() or None,
            "headers": final_action.headers or {},
            "return_to_caller": return_to_caller,
            "last_test_status": "configured",
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


def _step_read(item: dict[str, Any]) -> ODataStepConfig | ODataObjectStepConfig | ForeachODataStepConfig | PayloadStepConfig:
    if item.get("type") == "build_payload":
        return PayloadStepConfig(**item)
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
    final_action = FinalActionConfig(**draft.final_action_json) if draft.final_action_json else None
    return InputDraftRead(
        id=draft.id,
        name=draft.name,
        slug=draft.slug,
        scenario_key=draft.scenario_key,
        input_mode=draft.input_mode,  # type: ignore[arg-type]
        source_system=draft.source_system,
        contract=contract,
        odata_steps=odata_steps,
        final_action=final_action,
        parse_result=parse_result,
        endpoint_url=endpoint_url(draft.slug),
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )
