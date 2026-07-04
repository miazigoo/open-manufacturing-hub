from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.artifacts.service import get_artifact_or_404
from app.core.enums import ArtifactType, EventStatus, RunMode
from app.core.errors import BadRequestError, NotFoundError
from app.events.models import EventRun, EventStep, IntegrationEvent
from app.events.repository import get_event, get_event_with_timeline, list_events
from app.events.schemas import EventCreate, EventJournalItem
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


async def get_events(session: AsyncSession) -> list[IntegrationEvent]:
    return await list_events(session)


async def get_event_journal(session: AsyncSession) -> list[EventJournalItem]:
    events = await list_events(session)
    if not events:
        return []
    ids = [event.id for event in events]
    from app.external_errors.models import ExternalErrorRecord

    error_result = await session.execute(
        select(ExternalErrorRecord).where(ExternalErrorRecord.event_id.in_(ids)).order_by(ExternalErrorRecord.created_at.desc())
    )
    latest_errors = {}
    for record in error_result.scalars().all():
        latest_errors.setdefault(record.event_id, record)

    run_result = await session.execute(
        select(EventRun, EventStep)
        .join(EventStep, EventStep.run_id == EventRun.id)
        .where(EventRun.event_id.in_(ids))
        .order_by(EventRun.run_number.desc(), EventStep.step_order.desc())
    )
    latest_steps: dict[Any, EventStep] = {}
    for run, step in run_result.all():
        latest_steps.setdefault(run.event_id, step)

    rows: list[EventJournalItem] = []
    for event in events:
        external_error = latest_errors.get(event.id)
        step = latest_steps.get(event.id)
        title = external_error.human_title if external_error and external_error.human_title else _event_title(event)
        summary = external_error.human_summary if external_error and external_error.human_summary else _event_summary(event, step)
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
                requires_attention=event.status in {EventStatus.FAILED, EventStatus.RETRY_WAITING},
            )
        )
    return rows


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


async def _attach_external_errors(session: AsyncSession, event: IntegrationEvent) -> None:
    from app.external_errors.service import list_for_event

    records = await list_for_event(session, event.id)
    by_step = {record.step_id: record for record in records if record.step_id is not None}
    for run in event.runs:
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


def _event_title(event: IntegrationEvent) -> str:
    label = event.entity_id or event.correlation_id or str(event.id)[:8]
    return f"{event.event_type} {label}"


def _event_summary(event: IntegrationEvent, step: EventStep | None) -> str:
    if step and step.error_message:
        return step.error_message
    return f"{event.source_system} -> {event.target_system or 'unassigned'}"
