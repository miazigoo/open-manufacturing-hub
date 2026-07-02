from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.artifacts.service import get_artifact_or_404
from app.core.enums import ArtifactType, EventStatus, RunMode
from app.core.errors import BadRequestError, NotFoundError
from app.events.models import EventRun, IntegrationEvent
from app.events.repository import get_event, get_event_with_timeline, list_events
from app.events.schemas import EventCreate
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
    return event


async def get_events(session: AsyncSession) -> list[IntegrationEvent]:
    return await list_events(session)


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
