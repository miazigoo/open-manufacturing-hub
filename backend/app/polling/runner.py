from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.builtin.onec.odata import read_odata
from app.connectors.builtin.rest_connector import RESTConnector
from app.connectors.models import ConnectorInstance
from app.connectors.registry import registry
from app.core.enums import PollingCursorType, PollingJobStatus
from app.core.errors import BadRequestError, NotFoundError
from app.events.schemas import EventCreate
from app.events.service import create_event
from app.integration_master.payload_renderer import PayloadRenderError, render_payload_step
from app.integration_master.schemas import PayloadStepConfig
from app.mappings.engine import get_path
from app.packages_training.mock_external_api import import_order
from app.packages_training.mock_odata import query_mock_odata
from app.packages_training.mock_wms import import_orders
from app.polling.models import PollingJob, PollingJobRun, SourceEventCursor
from app.polling.repository import get_job
from app.sdk.types import ConnectorContext
from app.secrets.service import SecretResolver
from app.variables.paths import PathResolutionError, try_resolve_path
from app.variables.resolver import build_runtime_scope, render_template


class TargetSendFailed(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any]) -> None:
        super().__init__(message)
        self.details = details


async def run_once(
    session: AsyncSession,
    job_id: UUID,
    *,
    dry_run: bool = False,
    update_cursor: bool = True,
    allow_disabled: bool = False,
) -> PollingJobRun:
    job = await get_job(session, job_id)
    if job is None:
        raise NotFoundError("Polling job not found")
    if not job.enabled and not allow_disabled:
        raise BadRequestError("Polling job is disabled")
    if _job_mode(job) == "send_target":
        return await _run_send_target(session, job, dry_run=dry_run, update_cursor=update_cursor)
    return await _run_event_polling(session, job)


async def _run_event_polling(session: AsyncSession, job: PollingJob) -> PollingJobRun:
    connector_instance = await _source_connector(session, job)
    if connector_instance.connector_type != "onec":
        raise BadRequestError("Polling source connector must be onec")

    started_at = datetime.now(timezone.utc)
    cursor_before = _cursor_state(job)
    run = PollingJobRun(
        job_id=job.id,
        status=PollingJobStatus.RUNNING,
        started_at=started_at,
        cursor_before_json=cursor_before,
        cursor_after_json=cursor_before,
        details_json={"resource": job.resource, "query": job.query_json, "mode": "event_polling"},
    )
    session.add(run)
    job.status = PollingJobStatus.RUNNING
    await session.flush()

    try:
        query = _query_with_cursor(job)
        connector = registry.get(connector_instance.connector_type)
        connector_config = await SecretResolver(session).resolve_config(connector_instance.config_json)
        result = await connector.read_odata(connector_config, job.resource, query, ConnectorContext(metadata={"polling_job_id": str(job.id)}))
        if not result.success:
            raise BadRequestError(result.error_message or result.error_code or "1C OData read failed")
        created = 0
        skipped = 0
        created_ids: list[str] = []
        max_cursor = job.cursor_value
        last_event_id: UUID | None = None
        for item in result.items:
            entity_id = str(get_path(item, job.entity_id_field or "Ref_Key") or "")
            if not entity_id:
                skipped += 1
                continue
            item_hash = _content_hash(item)
            existing = (
                await session.execute(
                    select(SourceEventCursor).where(
                        SourceEventCursor.source_connector_id == connector_instance.id,
                        SourceEventCursor.source_resource == job.resource,
                        SourceEventCursor.source_entity_id == entity_id,
                        SourceEventCursor.event_type == job.event_type,
                    )
                )
            ).scalar_one_or_none()
            if existing is not None and existing.last_seen_hash == item_hash:
                skipped += 1
                continue
            event = await create_event(
                session,
                EventCreate(
                    correlation_id=str(get_path(item, job.correlation_id_field or "Number") or entity_id),
                    source_system=connector_instance.name,
                    target_system=job.target_system,
                    event_type=job.event_type,
                    entity_type=job.entity_type,
                    entity_id=entity_id,
                    payload=item,
                ),
            )
            created += 1
            last_event_id = event.id
            created_ids.append(str(event.id))
            now = datetime.now(timezone.utc)
            if existing is None:
                existing = SourceEventCursor(
                    source_connector_id=connector_instance.id,
                    source_resource=job.resource,
                    source_entity_id=entity_id,
                    event_type=job.event_type,
                )
                session.add(existing)
            existing.last_seen_hash = item_hash
            existing.last_seen_at = now
            existing.created_event_id = event.id
            cursor_candidate = str(get_path(item, job.updated_at_field or "") or "") if job.cursor_type == PollingCursorType.UPDATED_AT else None
            if cursor_candidate and (max_cursor is None or cursor_candidate > max_cursor):
                max_cursor = cursor_candidate
        finished_at = datetime.now(timezone.utc)
        cursor_after = dict(cursor_before)
        if max_cursor:
            job.cursor_value = max_cursor
            cursor_after["last_value"] = max_cursor
        _mark_success(job, run, finished_at, cursor_after)
        run.items_read = result.count
        run.events_created = created
        run.items_skipped = skipped
        run.sent_count = 0
        run.event_id = last_event_id
        run.details_json = {
            "mode": "event_polling",
            "resource": job.resource,
            "query": query,
            "items_read": result.count,
            "events_created": created,
            "items_skipped": skipped,
            "created_event_ids": created_ids,
            "request": result.request_payload,
        }
    except Exception as exc:
        _mark_failed(job, run, exc)
    await session.flush()
    return run


async def _run_send_target(session: AsyncSession, job: PollingJob, *, dry_run: bool, update_cursor: bool) -> PollingJobRun:
    connector_instance = await _source_connector(session, job)
    if connector_instance.connector_type != "onec":
        raise BadRequestError("Polling source connector must be onec")

    started_at = datetime.now(timezone.utc)
    config = _send_target_config(job)
    cursor_before = _cursor_state(job)
    run = PollingJobRun(
        job_id=job.id,
        status=PollingJobStatus.RUNNING,
        started_at=started_at,
        cursor_before_json=cursor_before,
        cursor_after_json=cursor_before,
        details_json={"mode": "send_target", "dry_run": dry_run, "resource": job.resource},
    )
    session.add(run)
    job.status = PollingJobStatus.RUNNING
    await session.flush()

    try:
        cursor_for_run, had_cursor = _cursor_for_run(config, cursor_before, started_at)
        query = _render_odata_query(config, cursor_for_run, started_at, had_cursor)
        items, odata_payload = await _read_odata_items(session, connector_instance, config, query)
        save_as = str((config.get("odata") or {}).get("save_as") or "orders")
        target = config.get("target") if isinstance(config.get("target"), dict) else {}
        empty_behavior = str(target.get("empty_result_behavior") or "do_nothing_success")
        target_payload: Any = None
        target_result: dict[str, Any] | None = None
        warning: str | None = None
        sent_count = 0

        if not items and empty_behavior in {"do_nothing_success", "mark_warning"}:
            warning = "Новых данных нет." if empty_behavior == "mark_warning" else None
            target_result = {"skipped": True, "reason": "Новых данных нет.", "dry_run": dry_run}
        else:
            target_payload = _render_target_payload(config, save_as, items, cursor_for_run, run, started_at)
            if dry_run:
                target_result = _dry_run_target_result(target, target_payload)
            else:
                target_result = await _send_target(target, target_payload, run)
                if not target_result.get("success"):
                    raise TargetSendFailed("Внешний API вернул ошибку. Cursor не обновлён.", target_result)
                sent_count = len(items)

        finished_at = datetime.now(timezone.utc)
        cursor_candidate = _cursor_after(config, cursor_before, items, finished_at)
        cursor_after = cursor_candidate if update_cursor and not dry_run else cursor_before
        if update_cursor and not dry_run:
            job.cursor_json = cursor_after
            job.cursor_value = str(cursor_after.get("last_value") or cursor_after.get("last_success_at") or "") or None

        _mark_success(job, run, finished_at, cursor_after)
        run.items_read = len(items)
        run.events_created = 0
        run.sent_count = sent_count
        run.items_skipped = 0 if items else len(items)
        run.details_json = {
            "mode": "send_target",
            "dry_run": dry_run,
            "update_cursor": update_cursor,
            "resource": job.resource,
            "query": query,
            "odata_request": odata_payload.get("request"),
            "odata_response": odata_payload.get("response"),
            "items_count": len(items),
            "sent_count": sent_count,
            "save_as": save_as,
            "target_payload": target_payload,
            "target_result": target_result,
            "cursor_candidate_json": cursor_candidate,
            "warning": warning,
        }
        if warning:
            run.error_message = warning
    except TargetSendFailed as exc:
        _mark_failed(job, run, exc)
        run.details_json = {**(run.details_json or {}), "target_result": exc.details, "cursor_not_updated": True}
    except Exception as exc:
        _mark_failed(job, run, exc)
    await session.flush()
    return run


async def _source_connector(session: AsyncSession, job: PollingJob) -> ConnectorInstance:
    connector_instance = await session.get(ConnectorInstance, job.source_connector_id)
    if connector_instance is None:
        raise NotFoundError("Source connector not found")
    return connector_instance


def _job_mode(job: PollingJob) -> str:
    config = job.config_json or {}
    return str(config.get("mode") or config.get("pattern_id") or "event_polling")


def _send_target_config(job: PollingJob) -> dict[str, Any]:
    config = dict(job.config_json or {})
    config.setdefault("mode", "send_target")
    config.setdefault("odata", {})
    config.setdefault("payload", {})
    config.setdefault("target", {})
    return config


def _cursor_state(job: PollingJob) -> dict[str, Any]:
    state = dict(job.cursor_json or {})
    if job.cursor_value and not state.get("last_value"):
        state["last_value"] = job.cursor_value
    return state


def _cursor_for_run(config: dict[str, Any], cursor_before: dict[str, Any], started_at: datetime) -> tuple[dict[str, Any], bool]:
    cursor = dict(cursor_before)
    had_cursor = bool(cursor.get("last_success_at") or cursor.get("last_value"))
    if had_cursor:
        return cursor, True
    first_run = config.get("first_run") if isinstance(config.get("first_run"), dict) else {}
    strategy = str(first_run.get("strategy") or "fixed_start_date")
    if strategy == "fixed_start_date":
        value = str(first_run.get("fixed_start_at") or "2026-01-01T00:00:00")
    elif strategy == "last_n_hours":
        hours = _positive_int(first_run.get("hours"), 24)
        value = _iso(started_at - timedelta(hours=hours))
    else:
        return cursor, False
    cursor.setdefault("last_success_at", value)
    cursor.setdefault("last_value", value)
    return cursor, False


def _render_odata_query(config: dict[str, Any], cursor: dict[str, Any], started_at: datetime, had_cursor: bool) -> dict[str, Any]:
    odata = config.get("odata") if isinstance(config.get("odata"), dict) else {}
    first_run = config.get("first_run") if isinstance(config.get("first_run"), dict) else {}
    filter_template = str(odata.get("filter") or "").strip()
    if not had_cursor and str(first_run.get("strategy") or "") == "no_cursor_filter":
        filter_template = _strip_cursor_clauses(filter_template)
    scope = {"cursor": cursor, "context": {"started_at": _iso(started_at), "run_id": "preview-run"}}
    query: dict[str, Any] = {}
    if filter_template:
        try:
            rendered_filter = str(render_template(filter_template, scope)).strip()
        except PathResolutionError as exc:
            raise BadRequestError("Не удалось подставить cursor.last_success_at в фильтр. Проверьте стратегию первого запуска.") from exc
        if "datetime''" in rendered_filter or "{{cursor." in rendered_filter:
            raise BadRequestError("Не удалось подставить cursor.last_success_at в фильтр. Проверьте стратегию первого запуска.")
        if rendered_filter:
            query["$filter"] = rendered_filter
    select = odata.get("select") or []
    if select:
        query["$select"] = select if isinstance(select, str) else ",".join(str(item) for item in select if str(item).strip())
    top = odata.get("top")
    if top:
        query["$top"] = int(top)
    orderby = odata.get("orderby")
    if orderby:
        query["$orderby"] = str(orderby)
    return query


def _strip_cursor_clauses(filter_template: str) -> str:
    if not filter_template:
        return ""
    clauses = [part.strip() for part in re.split(r"\s+and\s+", filter_template, flags=re.IGNORECASE) if part.strip()]
    kept = [part for part in clauses if "{{cursor." not in part]
    return " and ".join(kept)


async def _read_odata_items(session: AsyncSession, connector: ConnectorInstance, config: dict[str, Any], query: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    odata = config.get("odata") if isinstance(config.get("odata"), dict) else {}
    resource = str(odata.get("resource") or "").strip()
    if not resource:
        raise BadRequestError("Укажите OData resource для polling job.")
    connector_config = await SecretResolver(session).resolve_config(connector.config_json)
    mock_odata = (connector_config or {}).get("mock_odata")
    if isinstance(mock_odata, dict) and mock_odata:
        response = query_mock_odata(mock_odata, resource, query)
        items = response.get("value") if isinstance(response, dict) else []
        return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else [], {"request": {"mock": True, "resource": resource, "query": query}, "response": response}
    if odata.get("paginate") is False:
        connector_config = {**connector_config, "odata": {**(connector_config.get("odata") or {}), "max_pages": 1}}
    result = await read_odata(connector_config, resource, query)
    if not result.success:
        message = result.error_message or result.error_code or "1C OData read failed"
        if result.error_code and "AUTH" in result.error_code.upper():
            message = "1С не приняла логин или пароль."
        raise BadRequestError(message)
    return result.items, {"request": result.request_payload, "response": result.response_payload}


def _render_target_payload(config: dict[str, Any], save_as: str, items: list[dict[str, Any]], cursor: dict[str, Any], run: PollingJobRun, started_at: datetime) -> Any:
    payload_config = config.get("payload") if isinstance(config.get("payload"), dict) else {}
    variables = {
        save_as: items,
        "cursor": cursor,
    }
    scope = build_runtime_scope(
        request_body={},
        variables=variables,
        context={"run_id": str(run.id), "started_at": _iso(started_at)},
    )
    try:
        step = PayloadStepConfig(**payload_config)
        return render_payload_step(step, scope).rendered_body
    except PayloadRenderError:
        raise
    except Exception as exc:
        raise BadRequestError(f"Не удалось собрать target payload: {exc}") from exc


def _dry_run_target_result(target: dict[str, Any], payload: Any) -> dict[str, Any]:
    return {
        "success": True,
        "dry_run": True,
        "request": _target_request(target, payload),
        "response": {"dry_run": True, "would_send": True},
    }


async def _send_target(target: dict[str, Any], payload: Any, run: PollingJobRun) -> dict[str, Any]:
    request_payload = _target_request(target, payload)
    url = str(target.get("url") or "").strip()
    if not url:
        return {"success": False, "request": request_payload, "error_message": "Target URL is required"}
    training = _training_target_response(url, payload)
    if training is not None:
        status_code, body = training
        return {"success": status_code < 400 and body.get("success") is not False, "status_code": status_code, "request": request_payload, "response": body, "mock": True, "error_message": body.get("message") or body.get("error_message")}
    method = str(target.get("method") or "POST").upper()
    headers = target.get("headers") if isinstance(target.get("headers"), dict) else {}
    timeout = float(target.get("timeout_seconds") or 30)
    body_type = str(target.get("body_type") or "json")
    if body_type == "json":
        rest_payload = payload if isinstance(payload, dict) else {"body": payload}
        result = await RESTConnector().send({"url": url, "method": method, "headers": headers, "timeout_seconds": timeout}, rest_payload, ConnectorContext(run_id=run.id, dry_run=False, metadata={"polling_job_run_id": str(run.id)}))
        return {"success": result.success, "status_code": result.status_code, "request": result.request_payload, "response": result.response_payload, "error_code": result.error_code, "error_message": result.error_message}
    try:
        content = payload if isinstance(payload, (str, bytes)) else json.dumps(payload, ensure_ascii=False)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, content=content, headers={key: str(value) for key, value in headers.items()})
        try:
            body: Any = response.json()
        except Exception:
            body = {"text": response.text}
        return {"success": 200 <= response.status_code < 300, "status_code": response.status_code, "request": request_payload, "response": {"status_code": response.status_code, "body": body, "headers": dict(response.headers)}}
    except httpx.TimeoutException:
        return {"success": False, "request": request_payload, "error_message": "Внешний API не ответил за 30 секунд."}
    except Exception as exc:
        return {"success": False, "request": request_payload, "error_message": str(exc)}


def _target_request(target: dict[str, Any], payload: Any) -> dict[str, Any]:
    return {"method": str(target.get("method") or "POST").upper(), "url": target.get("url"), "headers": target.get("headers") or {}, "body_type": target.get("body_type") or "json", "body": payload}


def _training_target_response(url: str, payload: Any) -> tuple[int, dict[str, Any]] | None:
    if not isinstance(payload, dict):
        payload = {"body": payload}
    if "mock-wms/orders/import" in url:
        return import_orders(payload)
    if "mock-external-api/orders/import" in url:
        return import_order(payload)
    return None


def _cursor_after(config: dict[str, Any], cursor_before: dict[str, Any], items: list[dict[str, Any]], finished_at: datetime) -> dict[str, Any]:
    cursor = dict(cursor_before)
    cursor_config = config.get("cursor") if isinstance(config.get("cursor"), dict) else {}
    cursor_type = str(cursor_config.get("cursor_type") or "last_success_at")
    if cursor_type == "manual":
        return cursor
    if cursor_type == "field_max_value":
        field = str(cursor_config.get("source_field") or "orders[].Date")
        value = _max_item_value(items, field)
        if value is not None:
            cursor["last_value"] = value
        return cursor
    cursor["last_success_at"] = _iso(finished_at)
    return cursor


def _max_item_value(items: list[dict[str, Any]], source_field: str) -> str | None:
    path = source_field.strip()
    path = re.sub(r"^[^.]+\[\]\.", "", path)
    path = re.sub(r"^[^.]+\.", "", path) if path.startswith("orders.") else path
    values = [str(value) for item in items if (value := try_resolve_path(item, path)) not in (None, "")]
    return max(values) if values else None


def _mark_success(job: PollingJob, run: PollingJobRun, finished_at: datetime, cursor_after: dict[str, Any]) -> None:
    run.status = PollingJobStatus.SUCCESS
    run.finished_at = finished_at
    run.cursor_after_json = cursor_after
    job.status = PollingJobStatus.SUCCESS
    job.last_error = None
    job.last_run_at = finished_at
    job.next_run_at = _next_run_at(job, finished_at)


def _mark_failed(job: PollingJob, run: PollingJobRun, exc: Exception) -> None:
    finished_at = datetime.now(timezone.utc)
    run.status = PollingJobStatus.FAILED
    run.finished_at = finished_at
    run.error_message = str(exc) or exc.__class__.__name__
    run.cursor_after_json = dict(run.cursor_before_json or {})
    job.status = PollingJobStatus.FAILED
    job.last_error = run.error_message
    job.last_run_at = finished_at
    job.next_run_at = _next_run_at(job, finished_at)


def _next_run_at(job: PollingJob, finished_at: datetime) -> datetime | None:
    if not job.enabled or job.schedule_type == "manual_only":
        return None
    return finished_at + timedelta(seconds=job.interval_seconds)


def _query_with_cursor(job: PollingJob) -> dict[str, Any]:
    query = dict(job.query_json or {})
    if job.cursor_type == PollingCursorType.UPDATED_AT and job.cursor_value and job.updated_at_field:
        cursor_filter = f"{job.updated_at_field} gt datetime'{job.cursor_value}'"
        query["$filter"] = f"({query['$filter']}) and {cursor_filter}" if query.get("$filter") else cursor_filter
    return query


def _content_hash(item: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "")
