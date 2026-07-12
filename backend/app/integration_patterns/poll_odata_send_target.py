from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import repository as connector_repository
from app.connectors.models import ConnectorInstance
from app.core.enums import IntegrationFlowSourceType, IntegrationFlowTargetType, PollingCursorType
from app.core.errors import BadRequestError, NotFoundError
from app.integration_bus import repository as bus_repository
from app.integration_flows import repository as flow_repository
from app.integration_flows import service as integration_flows_service
from app.integration_flows.schemas import EndpointBuilderConfig, IntegrationFlowCreate
from app.integration_master.payload_renderer import PayloadRenderError, render_payload_step
from app.integration_master.schemas import PayloadStepConfig
from app.integration_patterns.schemas import (
    PollODataSendTargetCreateResponse,
    PollODataSendTargetPatternRequest,
    PollODataSendTargetPreviewResponse,
    PollODataSendTargetRunTestRequest,
    PollODataSendTargetRunTestResponse,
)
from app.packages_training.mock_odata import query_mock_odata
from app.polling import runner as polling_runner
from app.polling import service as polling_service
from app.polling.models import PollingJob
from app.polling.schemas import PollingJobCreate
from app.secrets.service import SecretResolver
from app.variables.paths import PathResolutionError
from app.variables.resolver import build_runtime_scope, render_template


async def preview_pattern(session: AsyncSession, request: PollODataSendTargetPatternRequest) -> PollODataSendTargetPreviewResponse:
    errors: list[str] = []
    warnings: list[str] = []
    connector = await _resolve_odata_connector(session, request, required=False)
    if connector is None:
        errors.append("OData connection не найдена. Выберите Training OData ERP или реальный 1C OData connector.")

    cursor = _preview_cursor(request)
    try:
        query = _render_query(request, cursor)
    except BadRequestError as exc:
        query = {}
        errors.append(str(exc))

    odata_items = _sample_orders(request)
    odata_payload: dict[str, Any] = {"mock": False}
    if connector is not None and query:
        try:
            connector_config = await SecretResolver(session).resolve_config(connector.config_json)
            mock_odata = connector_config.get("mock_odata") if isinstance(connector_config, dict) else None
            if isinstance(mock_odata, dict) and mock_odata:
                odata_payload = query_mock_odata(mock_odata, request.odata_step.resource, query)
                value = odata_payload.get("value") if isinstance(odata_payload, dict) else None
                if isinstance(value, list):
                    odata_items = [item for item in value if isinstance(item, dict)]
            else:
                warnings.append("Preview не выполняет live OData-запрос. Для реального подключения используйте Manual Test Run.")
        except Exception as exc:
            errors.append(_friendly_odata_error(str(exc)))

    target_payload = None
    try:
        target_payload = _render_payload(request, odata_items, cursor, run_id="preview-run-001", started_at="2026-07-12T12:00:00")
    except PayloadRenderError as exc:
        errors.append(exc.message)
    except Exception as exc:
        errors.append(f"Не удалось собрать target payload: {exc}")

    target_request = {
        "method": request.target.method,
        "url": request.target.url,
        "headers": request.target.headers,
        "body_source": request.target.body_source,
        "body_type": request.target.body_type,
        "timeout_seconds": request.target.timeout_seconds,
        "empty_result_behavior": request.target.empty_result_behavior,
        "body": target_payload,
    }
    if not request.target.url:
        errors.append("Target endpoint URL обязателен.")

    first_run_query = _render_query(request, _preview_cursor(request, first_run=True), first_run=True) if not errors else {}
    return PollODataSendTargetPreviewResponse(
        valid=not errors,
        errors=_dedupe(errors),
        warnings=_dedupe(warnings),
        schedule={"type": request.job.schedule_type, "interval_minutes": request.job.interval_minutes, "enabled_after_create": request.job.enabled_after_create},
        odata_request={"connection": _connector_label(connector, request), "resource": request.odata_step.resource, "query": query, "save_as": request.odata_step.save_as, "request": {"mock": bool(odata_payload.get("@odata.context"))}},
        first_run_filter=str(first_run_query.get("$filter") or query.get("$filter") or ""),
        odata_result=odata_items,
        target_payload=target_payload,
        target_request=target_request,
        cursor=cursor,
        run_history_hint={"items_count": len(odata_items), "sent_count": len(odata_items), "cursor_before_json": {}, "cursor_after_json": "updated after successful real run"},
        human_steps=[
            _schedule_label(request),
            f"read 1C OData {request.odata_step.resource}",
            f"save rows as {request.odata_step.save_as}",
            f"build payload {request.payload.save_as}",
            f"send {request.target.method} {request.target.url}",
            "write polling_job_runs history",
        ],
        advanced={"connector_id": str(connector.id) if connector else None, "odata_payload": odata_payload, "config_json": _job_config(request)},
    )


async def create_pattern(session: AsyncSession, request: PollODataSendTargetPatternRequest) -> PollODataSendTargetCreateResponse:
    await _ensure_slug_available(session, request.job.slug)
    connector = await _resolve_odata_connector(session, request, required=True)
    preview = await preview_pattern(session, request)
    if not preview.valid:
        raise BadRequestError("; ".join(preview.errors))
    flow = await integration_flows_service.create_flow(session, _flow_payload(request))
    job = await polling_service.create_job(
        session,
        PollingJobCreate(
            name=request.job.name,
            slug=request.job.slug,
            enabled=request.job.enabled_after_create,
            source_connector_id=connector.id,
            integration_flow_id=flow.id,
            target_system=_target_system(request.target.url),
            resource=request.odata_step.resource,
            query_json=_query_template(request),
            config_json=_job_config(request),
            event_type="ODataPollingOrders",
            entity_type="ODataPollingBatch",
            entity_id_field="Ref_Key",
            correlation_id_field="Number",
            updated_at_field="Date",
            cursor_json={},
            cursor_type=PollingCursorType.CUSTOM,
            schedule_type=request.job.schedule_type,
            interval_seconds=request.job.interval_minutes * 60,
        ),
    )
    return PollODataSendTargetCreateResponse(
        polling_job_id=job.id,
        integration_flow_id=flow.id,
        preview=preview,
        run_now_url=f"/api/polling-jobs/{job.id}/run-now",
        runs_url=f"/api/polling-jobs/{job.id}/runs",
        enabled=job.enabled,
        next_steps=[
            "Запустите manual test.",
            "Проверьте ответ WMS/API.",
            "Проверьте run history.",
            "Включите расписание после проверки.",
        ],
    )


async def run_test(session: AsyncSession, request: PollODataSendTargetRunTestRequest) -> PollODataSendTargetRunTestResponse:
    preview: PollODataSendTargetPreviewResponse | None = None
    if request.polling_job_id is not None:
        run = await polling_runner.run_once(session, request.polling_job_id, dry_run=request.dry_run, update_cursor=request.update_cursor, allow_disabled=True)
        return PollODataSendTargetRunTestResponse(success=run.status.value == "success", run=_run_dict(run), preview=None)
    if request.pattern is None:
        raise BadRequestError("Укажите polling_job_id или pattern для test run.")
    connector = await _resolve_odata_connector(session, request.pattern, required=True)
    preview = await preview_pattern(session, request.pattern)
    if not preview.valid:
        raise BadRequestError("; ".join(preview.errors))
    job = await polling_service.create_job(
        session,
        PollingJobCreate(
            name=f"{request.pattern.job.name} Test",
            slug=f"{request.pattern.job.slug}-test-{datetime.now(timezone.utc).timestamp():.0f}",
            enabled=False,
            source_connector_id=connector.id,
            target_system=_target_system(request.pattern.target.url),
            resource=request.pattern.odata_step.resource,
            query_json=_query_template(request.pattern),
            config_json=_job_config(request.pattern),
            event_type="ODataPollingOrders",
            entity_type="ODataPollingBatch",
            cursor_type=PollingCursorType.CUSTOM,
            schedule_type="manual_only",
            interval_seconds=request.pattern.job.interval_minutes * 60,
        ),
    )
    run = await polling_runner.run_once(session, job.id, dry_run=request.dry_run, update_cursor=request.update_cursor, allow_disabled=True)
    run_data = _run_dict(run)
    await session.rollback()
    return PollODataSendTargetRunTestResponse(success=run_data["status"] == "success", run=run_data, preview=preview)


async def _resolve_odata_connector(session: AsyncSession, request: PollODataSendTargetPatternRequest, *, required: bool) -> ConnectorInstance | None:
    if request.odata_step.connection_id:
        connector = await connector_repository.get_instance(session, request.odata_step.connection_id)
        if connector is not None:
            return connector
    if request.odata_step.connection_name:
        connector = await connector_repository.get_by_name(session, request.odata_step.connection_name)
        if connector is not None:
            return connector
    connector = await connector_repository.get_by_name(session, "Training OData ERP")
    if connector is not None:
        return connector
    result = await session.execute(select(ConnectorInstance).where(ConnectorInstance.connector_type == "onec").limit(1))
    connector = result.scalar_one_or_none()
    if connector is None and required:
        raise NotFoundError("OData connection not found")
    return connector


def _job_config(request: PollODataSendTargetPatternRequest) -> dict[str, Any]:
    return {
        "mode": "send_target",
        "pattern_id": "poll_odata_send_target",
        "schedule": {"type": request.job.schedule_type, "interval_minutes": request.job.interval_minutes},
        "odata": {
            "connection_id": str(request.odata_step.connection_id) if request.odata_step.connection_id else None,
            "connection_name": request.odata_step.connection_name,
            "resource": request.odata_step.resource,
            "filter": request.odata_step.filter,
            "select": request.odata_step.select,
            "top": request.odata_step.top,
            "orderby": request.odata_step.orderby,
            "paginate": request.odata_step.paginate,
            "save_as": request.odata_step.save_as,
            "required": request.odata_step.required,
        },
        "first_run": request.first_run.model_dump(mode="json"),
        "cursor": request.cursor.model_dump(mode="json"),
        "payload": request.payload.model_dump(mode="json"),
        "target": request.target.model_dump(mode="json"),
    }


def _query_template(request: PollODataSendTargetPatternRequest) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if request.odata_step.filter:
        query["$filter"] = request.odata_step.filter
    if request.odata_step.select:
        query["$select"] = ",".join(request.odata_step.select)
    if request.odata_step.top:
        query["$top"] = request.odata_step.top
    if request.odata_step.orderby:
        query["$orderby"] = request.odata_step.orderby
    return query


def _render_query(request: PollODataSendTargetPatternRequest, cursor: dict[str, Any], *, first_run: bool = False) -> dict[str, Any]:
    filter_template = request.odata_step.filter or ""
    if first_run and request.first_run.strategy == "no_cursor_filter":
        filter_template = _strip_cursor_clauses(filter_template)
    query: dict[str, Any] = {}
    if filter_template:
        scope = {"cursor": cursor, "context": {"run_id": "preview-run-001", "started_at": "2026-07-12T12:00:00"}}
        try:
            rendered = str(render_template(filter_template, scope)).strip()
        except PathResolutionError as exc:
            raise BadRequestError("Не удалось подставить cursor.last_success_at в фильтр. Проверьте стратегию первого запуска.") from exc
        if "datetime''" in rendered:
            raise BadRequestError("Не удалось подставить cursor.last_success_at в фильтр. Проверьте стратегию первого запуска.")
        if rendered:
            query["$filter"] = rendered
    if request.odata_step.select:
        query["$select"] = ",".join(request.odata_step.select)
    if request.odata_step.top:
        query["$top"] = request.odata_step.top
    if request.odata_step.orderby:
        query["$orderby"] = request.odata_step.orderby
    return query


def _strip_cursor_clauses(filter_template: str) -> str:
    parts = [part.strip() for part in re.split(r"\s+and\s+", filter_template, flags=re.IGNORECASE) if part.strip()]
    return " and ".join(part for part in parts if "{{cursor." not in part)


def _preview_cursor(request: PollODataSendTargetPatternRequest, *, first_run: bool = False) -> dict[str, Any]:
    if request.first_run.strategy == "last_n_hours":
        value = (datetime(2026, 7, 12, 12, 0, 0, tzinfo=timezone.utc) - timedelta(hours=request.first_run.hours)).replace(tzinfo=None).isoformat()
    elif request.first_run.strategy == "no_cursor_filter" and first_run:
        return {}
    else:
        value = request.first_run.fixed_start_at
    return {"last_success_at": value, "last_value": value}


def _render_payload(request: PollODataSendTargetPatternRequest, items: list[dict[str, Any]], cursor: dict[str, Any], *, run_id: str, started_at: str) -> Any:
    variables = {request.odata_step.save_as: items, "cursor": cursor}
    scope = build_runtime_scope(request_body={}, variables=variables, context={"run_id": run_id, "started_at": started_at})
    step = PayloadStepConfig(**request.payload.model_dump(mode="json"))
    return render_payload_step(step, scope).rendered_body


def _flow_payload(request: PollODataSendTargetPatternRequest) -> IntegrationFlowCreate:
    return IntegrationFlowCreate(
        name=request.job.name,
        slug=request.job.slug,
        description="Created from Poll 1C OData -> Send Target wizard. Runtime entrypoint is Polling Jobs, not inbound HTTP.",
        enabled=False,
        source_type=IntegrationFlowSourceType.MANUAL,
        target_type=IntegrationFlowTargetType.WMS if _target_system(request.target.url) == "WMS" else IntegrationFlowTargetType.EXTERNAL_API,
        endpoint=EndpointBuilderConfig(input_mode="json", response_mode="accepted_event"),
        matcher_group_json={"mode": "all", "rules": [{"type": "always"}]},
        action_json={"type": "poll_odata_send_target", "operation": "poll_odata_send_target", "url": request.target.url, "method": request.target.method},
        response_config_json={"pattern_id": "poll_odata_send_target", "run_via": "/api/polling-jobs/{id}/run-now"},
        builder_json=_builder_json(request),
        test_payload_json={"manual_run": True, "polling_job_slug": request.job.slug},
    )


def _builder_json(request: PollODataSendTargetPatternRequest) -> dict[str, Any]:
    return {
        "steps": [
            {
                "id": "read_odata_orders",
                "type": "odata_query",
                "name": "Read 1C OData orders",
                "connection": request.odata_step.connection_name or "Training OData ERP",
                "resource": request.odata_step.resource,
                "filter": request.odata_step.filter,
                "select": request.odata_step.select,
                "top": request.odata_step.top,
                "orderby": request.odata_step.orderby,
                "paginate": request.odata_step.paginate,
                "save_as": request.odata_step.save_as,
                "required": request.odata_step.required,
            },
            {
                "id": "build_target_payload",
                "type": "build_payload",
                "name": "Build target payload",
                **request.payload.model_dump(mode="json", exclude_none=True),
            },
            {
                "id": "send_target",
                "type": "call_endpoint",
                "name": "Send target endpoint",
                "method": request.target.method,
                "url": request.target.url,
                "headers": request.target.headers,
                "body": f"{{{{{request.target.body_source}}}}}",
                "body_type": request.target.body_type,
                "timeout_seconds": request.target.timeout_seconds,
                "save_response_as": "target_response",
            },
        ],
        "metadata": {"pattern_id": "poll_odata_send_target", "schedule_type": request.job.schedule_type, "cursor": request.cursor.model_dump(mode="json")},
    }


async def _ensure_slug_available(session: AsyncSession, slug: str) -> None:
    if await flow_repository.get_by_slug(session, slug):
        raise BadRequestError(f"Integration Flow со slug {slug} уже существует. Выберите другой slug.")
    if await bus_repository.get_endpoint_by_slug(session, slug):
        raise BadRequestError(f"Endpoint /api/bus/in/{slug} уже существует. Выберите другой slug.")
    result = await session.execute(select(PollingJob.id).where(PollingJob.slug == slug).limit(1))
    if result.scalar_one_or_none() is not None:
        raise BadRequestError(f"Polling job со slug {slug} уже существует. Выберите другой slug.")


def _sample_orders(request: PollODataSendTargetPatternRequest) -> list[dict[str, Any]]:
    fields = request.odata_step.select or ["Ref_Key", "Number", "Date", "Posted", "Контрагент_Key"]
    row = {field: _sample_value(field) for field in fields}
    row.setdefault("Ref_Key", "44444444-4444-4444-4444-444444444444")
    row.setdefault("Number", "SO-1001")
    row.setdefault("Date", "2026-07-01T10:00:00")
    row.setdefault("Posted", True)
    return [row]


def _sample_value(field: str) -> Any:
    lower = field.lower()
    if field.endswith("_Key") or field == "Ref_Key":
        return "11111111-1111-1111-1111-111111111111"
    if lower == "number":
        return "SO-1001"
    if lower == "date":
        return "2026-07-01T10:00:00"
    if lower == "posted":
        return True
    return f"sample_{field}"


def _run_dict(run: Any) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "job_id": str(run.job_id),
        "status": run.status.value if hasattr(run.status, "value") else str(run.status),
        "items_read": run.items_read,
        "events_created": run.events_created,
        "sent_count": run.sent_count,
        "items_skipped": run.items_skipped,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "error_message": run.error_message,
        "event_id": str(run.event_id) if run.event_id else None,
        "cursor_before_json": run.cursor_before_json,
        "cursor_after_json": run.cursor_after_json,
        "details_json": run.details_json,
    }


def _target_system(url: str) -> str:
    return "WMS" if "wms" in (url or "").lower() else "External API"


def _schedule_label(request: PollODataSendTargetPatternRequest) -> str:
    if request.job.schedule_type == "manual_only":
        return "manual only"
    return f"every {request.job.interval_minutes} minutes"


def _connector_label(connector: ConnectorInstance | None, request: PollODataSendTargetPatternRequest) -> str:
    return connector.name if connector is not None else request.odata_step.connection_name or "Training OData ERP"


def _friendly_odata_error(message: str) -> str:
    if re.search(r"\b(401|403|unauthorized|forbidden|auth)\b", message, re.I):
        return "1С не приняла логин или пароль."
    return message


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
