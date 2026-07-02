from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.connectors.registry import registry
from app.core.enums import PollingCursorType, PollingJobStatus
from app.core.errors import BadRequestError, NotFoundError
from app.events.schemas import EventCreate
from app.events.service import create_event
from app.mappings.engine import get_path
from app.polling.models import PollingJob, PollingJobRun, SourceEventCursor
from app.polling.repository import get_job
from app.sdk.types import ConnectorContext


async def run_once(session: AsyncSession, job_id: UUID) -> PollingJobRun:
    job = await get_job(session, job_id)
    if job is None:
        raise NotFoundError("Polling job not found")
    if not job.enabled:
        raise BadRequestError("Polling job is disabled")
    connector_instance = await session.get(ConnectorInstance, job.source_connector_id)
    if connector_instance is None:
        raise NotFoundError("Source connector not found")
    if connector_instance.connector_type != "onec":
        raise BadRequestError("Polling source connector must be onec")

    started_at = datetime.now(timezone.utc)
    run = PollingJobRun(job_id=job.id, status=PollingJobStatus.RUNNING, started_at=started_at, details_json={"resource": job.resource, "query": job.query_json})
    session.add(run)
    job.status = PollingJobStatus.RUNNING
    await session.flush()

    try:
        query = _query_with_cursor(job)
        connector = registry.get(connector_instance.connector_type)
        result = await connector.read_odata(connector_instance.config_json, job.resource, query, ConnectorContext(metadata={"polling_job_id": str(job.id)}))
        if not result.success:
            raise BadRequestError(result.error_message or result.error_code or "1C OData read failed")
        created = 0
        skipped = 0
        created_ids: list[str] = []
        max_cursor = job.cursor_value
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
        run.status = PollingJobStatus.SUCCESS
        run.items_read = result.count
        run.events_created = created
        run.items_skipped = skipped
        run.finished_at = finished_at
        run.details_json = {"resource": job.resource, "query": query, "items_read": result.count, "events_created": created, "items_skipped": skipped, "created_event_ids": created_ids, "request": result.request_payload}
        job.status = PollingJobStatus.SUCCESS
        job.last_error = None
        job.last_run_at = finished_at
        job.next_run_at = finished_at + timedelta(seconds=job.interval_seconds)
        if max_cursor:
            job.cursor_value = max_cursor
    except Exception as exc:
        finished_at = datetime.now(timezone.utc)
        run.status = PollingJobStatus.FAILED
        run.finished_at = finished_at
        run.error_message = str(exc) or exc.__class__.__name__
        job.status = PollingJobStatus.FAILED
        job.last_error = run.error_message
        job.last_run_at = finished_at
        job.next_run_at = finished_at + timedelta(seconds=job.interval_seconds)
    await session.flush()
    return run


def _query_with_cursor(job: PollingJob) -> dict[str, Any]:
    query = dict(job.query_json or {})
    if job.cursor_type == PollingCursorType.UPDATED_AT and job.cursor_value and job.updated_at_field:
        cursor_filter = f"{job.updated_at_field} gt datetime'{job.cursor_value}'"
        query["$filter"] = f"({query['$filter']}) and {cursor_filter}" if query.get("$filter") else cursor_filter
    return query


def _content_hash(item: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
