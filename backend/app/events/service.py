from datetime import datetime, timezone, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, defer, noload

from app.artifacts.models import Artifact
from app.artifacts.service import get_artifact_or_404
from app.core.enums import ArtifactType, EnterpriseQueueStatus, EventStatus, IncidentStatus, RunMode
from app.core.errors import BadRequestError, NotFoundError
from app.enterprise_runtime.models import IntegrationQueueMessage
from app.events.models import EventRun, EventStep, IntegrationEvent
from app.events.repository import get_event, get_event_with_timeline, list_events, list_events_page
from app.events.schemas import (
    EventCreate,
    EventDashboardSummary,
    EventJournalItem,
    EventJournalPageResponse,
    EventOverview,
    EventQueueInfo,
    EventRunSummary,
    EventStepSummary,
    EventSummary,
)
from app.execution.engine import ExecutionEngine
from app.execution.exceptions import StepNotFoundError
from app.execution.registry import registry as step_registry


async def create_event(session: AsyncSession, request: EventCreate) -> IntegrationEvent:
    event = IntegrationEvent(
        correlation_id=request.correlation_id,
        source_system=request.source_system,
        target_system=request.target_system,
        event_type=request.event_type,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        status=EventStatus.NEW,
    )
    session.add(event)
    await session.flush()
    await ExecutionEngine(session).execute_event(event.id, mode=RunMode.NORMAL, initial_payload=request.payload)
    await session.refresh(event)
    return event


async def get_event_or_404(session: AsyncSession, event_id: UUID) -> IntegrationEvent:
    event = await get_event(session, event_id)
    if event is None:
        raise NotFoundError("Event not found")
    return event


async def get_timeline_or_404(session: AsyncSession, event_id: UUID) -> IntegrationEvent:
    event = await get_event_with_timeline(session, event_id)
    if event is None:
        raise NotFoundError("Event not found")
    event.runs.sort(key=lambda run: run.run_number)
    for run in event.runs:
        run.steps.sort(key=lambda step: step.step_order)
    await _attach_external_errors(session, event)
    return event


async def get_event_overview(session: AsyncSession, event_id: UUID, limit: int = 20, offset: int = 0, *, brief: bool = False, before_run: int | None = None) -> EventOverview:
    result = await session.execute(
        select(IntegrationEvent)
        .where(IntegrationEvent.id == event_id)
        .options(
            noload(IntegrationEvent.runs),
            noload(IntegrationEvent.artifacts),
        )
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise NotFoundError("Event not found")

    # Load queue info if exists (without fetching full payload)
    queue_item = await queue_info_for_event(session, event_id)
    queue_info = None
    if queue_item:
        queue_info = EventQueueInfo(**queue_item)

    if brief:
        stmt = select(EventRun.id, EventRun.event_id, EventRun.run_number, EventRun.mode, EventRun.status,
                      EventRun.parent_run_id, EventRun.workflow_id, EventRun.workflow_name, EventRun.workflow_version,
                      EventRun.started_at, EventRun.finished_at)
    else:
        stmt = select(EventRun).options(*_run_metadata_options())
    stmt = stmt.where(EventRun.event_id == event_id)
    if before_run is not None:
        stmt = stmt.where(EventRun.run_number < before_run)
    result = await session.execute(stmt.order_by(EventRun.run_number.desc()).offset(offset).limit(limit + 1))
    if brief:
        rows = result.mappings().all()
        run_summaries = [EventRunSummary.model_validate(row) for row in rows[:limit]]
    else:
        rows = result.scalars().all()
        runs = rows[:limit]
        await _attach_external_errors_to_runs(session, event_id, runs)
        for run in runs:
            run.steps.sort(key=lambda step: step.step_order)
        run_summaries = [EventRunSummary.model_validate(run) for run in runs]
    has_more = len(rows) > limit

    return EventOverview(
        event=EventSummary.model_validate(event),
        queue_item=queue_info,
        runs=run_summaries,
        has_more_runs=has_more,
        next_runs_cursor=str(run_summaries[-1].run_number) if has_more else None,
    )


def _run_metadata_options():
    return (
        selectinload(EventRun.steps).selectinload(EventStep.artifacts).defer(Artifact.content_json),
        selectinload(EventRun.artifacts).defer(Artifact.content_json),
    )


async def run_metadata(session: AsyncSession, event_id: UUID, run_id: UUID) -> EventRunSummary:
    stmt = select(EventRun).where(EventRun.event_id == event_id, EventRun.id == run_id).options(*_run_metadata_options())
    run = (await session.scalars(stmt)).one_or_none()
    if run is None:
        raise NotFoundError("Run not found")
    run.steps.sort(key=lambda step: step.step_order)
    await _attach_external_errors_to_runs(session, event_id, [run])
    return EventRunSummary.model_validate(run)


async def get_dashboard_summary(session: AsyncSession) -> EventDashboardSummary:
    now_utc = datetime.now(timezone.utc)
    # Start of day (midnight) in UTC
    period_start = datetime(now_utc.year, now_utc.month, now_utc.day, 0, 0, 0, tzinfo=timezone.utc)
    # Next midnight in UTC
    period_end = period_start + timedelta(days=1)

    # Events today
    events_today = await session.scalar(
        select(func.count(IntegrationEvent.id))
        .where(IntegrationEvent.created_at >= period_start, IntegrationEvent.created_at < period_end)
    ) or 0

    # Failed events today
    failed_today = await session.scalar(
        select(func.count(IntegrationEvent.id))
        .where(
            IntegrationEvent.status == EventStatus.FAILED,
            IntegrationEvent.created_at >= period_start,
            IntegrationEvent.created_at < period_end,
        )
    ) or 0

    # retry_waiting across all events
    retry_waiting = await session.scalar(
        select(func.count(IntegrationEvent.id))
        .where(IntegrationEvent.status == EventStatus.RETRY_WAITING)
    ) or 0

    # Open incidents
    from app.incidents.models import Incident
    open_incidents = await session.scalar(
        select(func.count(Incident.id))
        .where(Incident.status == IncidentStatus.OPEN)
    ) or 0

    # Queue backlog (waiting + retry_waiting)
    queue_backlog = await session.scalar(
        select(func.count(IntegrationQueueMessage.id))
        .where(IntegrationQueueMessage.status.in_([EnterpriseQueueStatus.WAITING, EnterpriseQueueStatus.RETRY_WAITING]))
    ) or 0

    # Queue processing
    queue_processing = await session.scalar(
        select(func.count(IntegrationQueueMessage.id))
        .where(IntegrationQueueMessage.status == EnterpriseQueueStatus.PROCESSING)
    ) or 0

    # Latest 6 failures across all history
    fail_res = await session.execute(
        select(IntegrationEvent)
        .where(IntegrationEvent.status == EventStatus.FAILED)
        .order_by(IntegrationEvent.created_at.desc())
        .limit(6)
    )
    latest_failures = [EventSummary.model_validate(e) for e in fail_res.scalars().all()]

    return EventDashboardSummary(
        timezone="UTC",
        period_start=period_start,
        period_end=period_end,
        events_today=events_today,
        failed_today=failed_today,
        retry_waiting=retry_waiting,
        open_incidents=open_incidents,
        queue_backlog=queue_backlog,
        queue_processing=queue_processing,
        latest_failures=latest_failures,
    )


async def get_events(session: AsyncSession) -> list[IntegrationEvent]:
    return await list_events(session)


async def _hydrate_journal_items(session: AsyncSession, events: list[IntegrationEvent]) -> list[EventJournalItem]:
    if not events:
        return []
    ids = [event.id for event in events]
    from app.external_errors.models import ExternalErrorRecord

    err_subq = (
        select(
            ExternalErrorRecord.event_id,
            ExternalErrorRecord.human_title,
            ExternalErrorRecord.human_summary,
            ExternalErrorRecord.operation,
            ExternalErrorRecord.normalized_code,
            ExternalErrorRecord.external_error_message,
            ExternalErrorRecord.hint,
            func.row_number()
            .over(
                partition_by=ExternalErrorRecord.event_id,
                order_by=(ExternalErrorRecord.created_at.desc(), ExternalErrorRecord.id.desc()),
            )
            .label("rn"),
        )
        .where(ExternalErrorRecord.event_id.in_(ids))
        .subquery()
    )
    err_result = await session.execute(select(err_subq).where(err_subq.c.rn == 1))
    latest_errors = {row.event_id: row for row in err_result.all()}

    step_subq = (
        select(
            EventRun.event_id,
            EventStep.step_name,
            EventStep.error_code,
            EventStep.error_message,
            func.row_number()
            .over(
                partition_by=EventRun.event_id,
                order_by=(EventRun.run_number.desc(), EventStep.step_order.desc(), EventStep.id.desc()),
            )
            .label("rn"),
        )
        .join(EventStep, EventStep.run_id == EventRun.id)
        .where(EventRun.event_id.in_(ids))
        .subquery()
    )
    step_result = await session.execute(select(step_subq).where(step_subq.c.rn == 1))
    latest_steps = {row.event_id: row for row in step_result.all()}

    queue_subq = (
        select(
            IntegrationQueueMessage.event_id,
            IntegrationQueueMessage.status,
            IntegrationQueueMessage.attempts,
            IntegrationQueueMessage.max_attempts,
            IntegrationQueueMessage.next_retry_at,
            func.row_number()
            .over(
                partition_by=IntegrationQueueMessage.event_id,
                order_by=(IntegrationQueueMessage.created_at.desc(), IntegrationQueueMessage.id.desc()),
            )
            .label("rn"),
        )
        .where(IntegrationQueueMessage.event_id.in_(ids))
        .subquery()
    )
    queue_result = await session.execute(select(queue_subq).where(queue_subq.c.rn == 1))
    latest_queue = {row.event_id: row for row in queue_result.all()}

    rows: list[EventJournalItem] = []
    for event in events:
        external_error = latest_errors.get(event.id)
        step = latest_steps.get(event.id)
        queue = latest_queue.get(event.id)
        title = external_error.human_title if external_error and external_error.human_title else _event_title(event)
        summary = external_error.human_summary if external_error and external_error.human_summary else _event_summary(event, step)
        q_status_val = (
            queue.status.value
            if (queue and hasattr(queue.status, "value"))
            else (str(queue.status) if queue else None)
        )
        requires_attention = (
            event.status in {EventStatus.FAILED, EventStatus.RETRY_WAITING}
            or (q_status_val in {"retry_waiting", "dlq", "failed"})
        )
        rows.append(
            EventJournalItem(
                id=event.id,
                correlation_id=event.correlation_id,
                source_system=event.source_system,
                target_system=event.target_system,
                event_type=event.event_type,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                status=event.status,
                pinned=event.pinned,
                created_at=event.created_at,
                human_title=title,
                human_summary=summary,
                business_key=event.entity_id or event.correlation_id,
                operation=external_error.operation if external_error else None,
                document_type=event.entity_type,
                document_number=event.entity_id,
                source_display=event.source_system,
                target_display=event.target_system,
                last_step=step.step_name if step else None,
                last_error_code=(external_error.normalized_code if external_error else step.error_code if step else None),
                last_error_summary=(external_error.human_summary if external_error else step.error_message if step else None),
                last_external_error_message=external_error.external_error_message if external_error else None,
                hint=external_error.hint if external_error else None,
                requires_attention=requires_attention,
                queue_status=q_status_val,
                queue_attempts=queue.attempts if queue else None,
                queue_max_attempts=queue.max_attempts if queue else None,
                queue_next_retry_at=queue.next_retry_at if queue else None,
            )
        )
    return rows


async def get_event_journal(session: AsyncSession) -> list[EventJournalItem]:
    events = await list_events(session)
    return await _hydrate_journal_items(session, events)


async def get_event_journal_page(
    session: AsyncSession,
    *,
    status: EventStatus | None = None,
    event_type: str | None = None,
    source: str | None = None,
    target: str | None = None,
    q: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    cursor: str | None = None,
) -> EventJournalPageResponse:
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from cannot be after date_to")

    events, next_cursor, has_more = await list_events_page(
        session,
        status=status,
        event_type=event_type,
        source=source,
        target=target,
        q=q,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        cursor=cursor,
    )
    items = await _hydrate_journal_items(session, events)
    return EventJournalPageResponse(items=items, next_cursor=next_cursor, has_more=has_more)


async def queue_info_for_event(session: AsyncSession, event_id: UUID) -> dict[str, Any] | None:
    stmt = (
        select(IntegrationQueueMessage)
        .where(IntegrationQueueMessage.event_id == event_id)
        .options(
            defer(IntegrationQueueMessage.payload_json),
            defer(IntegrationQueueMessage.original_payload_json),
        )
        .order_by(IntegrationQueueMessage.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    item = result.scalar_one_or_none()
    if item is None:
        return None
    return {
        "id": item.id,
        "status": item.status.value if hasattr(item.status, "value") else str(item.status),
        "attempts": item.attempts,
        "max_attempts": item.max_attempts,
        "next_retry_at": item.next_retry_at,
        "locked_by": item.locked_by,
        "locked_until": item.locked_until,
        "last_error": item.last_error,
        "timeline_link": item.timeline_link,
    }


async def set_pinned(session: AsyncSession, event_id: UUID, pinned: bool) -> IntegrationEvent:
    event = await get_event_or_404(session, event_id)
    event.pinned = pinned
    await session.flush()
    return event


async def replay_event(session: AsyncSession, event_id: UUID, mode: RunMode = RunMode.REPLAY, start_from_step: str | None = None) -> EventRun:
    _validate_start_step(start_from_step)
    await get_event_or_404(session, event_id)
    return await ExecutionEngine(session).execute_event(event_id, mode=mode, start_from_step=start_from_step)


async def replay_from_run_step(session: AsyncSession, run_id: UUID, step_name: str) -> EventRun:
    run = await session.get(EventRun, run_id)
    if run is None:
        raise NotFoundError("Run not found")
    return await replay_event(session, run.event_id, mode=RunMode.REPLAY_FROM_STEP, start_from_step=step_name)


async def dry_run_event(session: AsyncSession, event_id: UUID) -> EventRun:
    return await replay_event(session, event_id, mode=RunMode.DRY_RUN)


async def edit_replay_artifact(
    session: AsyncSession, artifact_id: UUID, edited_content: dict[str, Any], start_from_step: str
) -> EventRun:
    _validate_start_step(start_from_step)
    source_artifact = await get_artifact_or_404(session, artifact_id)
    await get_event_or_404(session, source_artifact.event_id)
    return await ExecutionEngine(session).execute_event(
        source_artifact.event_id,
        mode=RunMode.EDIT_REPLAY,
        start_from_step=start_from_step,
        edited_artifact=edited_content,
    )


async def _payload_for_event(session: AsyncSession, event_id: UUID) -> dict[str, Any]:
    result = await session.execute(
        select(Artifact)
        .where(Artifact.event_id == event_id, Artifact.artifact_type == ArtifactType.RAW_PAYLOAD.value)
        .order_by(Artifact.created_at.asc())
        .limit(1)
    )
    artifact = result.scalar_one_or_none()
    if artifact is None:
        raise NotFoundError("Original payload artifact not found")
    return artifact.content_json


def _validate_start_step(step_name: str | None) -> None:
    if step_name is None:
        return
    try:
        step_registry.get(step_name)
    except StepNotFoundError as exc:
        raise BadRequestError(f"Unknown step: {step_name}") from exc


async def _attach_external_errors_to_runs(session: AsyncSession, event_id: UUID, runs: list[EventRun]) -> None:
    from app.external_errors.models import ExternalErrorRecord

    step_ids = [step.id for run in runs for step in run.steps]
    if not step_ids:
        return
    records = await session.scalars(select(ExternalErrorRecord).where(
        ExternalErrorRecord.event_id == event_id, ExternalErrorRecord.step_id.in_(step_ids)
    ).order_by(ExternalErrorRecord.created_at, ExternalErrorRecord.id))
    by_step = {record.step_id: record for record in records if record.step_id is not None}
    for run in runs:
        for step in run.steps:
            record = by_step.get(step.id)
            if record is None:
                continue
            setattr(step, "human_title", record.human_title)
            setattr(step, "human_summary", record.human_summary)
            setattr(step, "developer_message", record.developer_message)
            setattr(step, "hint", record.hint)
            setattr(step, "external_error_record_id", record.id)
            setattr(step, "external_error", record)


async def _attach_external_errors(session: AsyncSession, event: IntegrationEvent) -> None:
    await _attach_external_errors_to_runs(session, event.id, list(event.runs))


def _event_title(event: IntegrationEvent) -> str:
    label = event.entity_id or event.correlation_id or str(event.id)[:8]
    return f"{event.event_type} {label}"


def _event_summary(event: IntegrationEvent, step: EventStep | None) -> str:
    if step and step.error_message:
        return step.error_message
    return f"{event.source_system} -> {event.target_system or 'unassigned'}"
