from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.artifacts.service import create_artifact, get_artifact_or_404
from app.core.enums import ArtifactType, EventStatus, RunMode, RunStatus
from app.core.errors import BadRequestError, NotFoundError
from app.events.models import EventRun, IntegrationEvent
from app.events.repository import get_event, get_event_with_timeline, latest_run, list_events, next_run_number
from app.events.schemas import EventCreate
from app.pipeline.context import PipelineContext
from app.pipeline.steps import STEP_NAMES
from app.pipeline.engine import PipelineEngine


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

    run = EventRun(event_id=event.id, run_number=1, mode=RunMode.NORMAL, status=RunStatus.CREATED)
    session.add(run)
    await session.flush()

    await PipelineEngine(session).run(event, run, PipelineContext(payload=request.payload, mode=RunMode.NORMAL))
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
    event = await get_event_or_404(session, event_id)
    parent = await latest_run(session, event_id)
    payload = await _payload_for_event(session, event_id)
    run = EventRun(
        event_id=event.id,
        run_number=await next_run_number(session, event.id),
        mode=mode,
        status=RunStatus.CREATED,
        parent_run_id=parent.id if parent else None,
    )
    session.add(run)
    await session.flush()
    return await PipelineEngine(session).run(event, run, PipelineContext(payload=payload, mode=mode, start_from_step=start_from_step))


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
    event = await get_event_or_404(session, source_artifact.event_id)
    parent = await latest_run(session, event.id)
    run = EventRun(
        event_id=event.id,
        run_number=await next_run_number(session, event.id),
        mode=RunMode.EDIT_REPLAY,
        status=RunStatus.CREATED,
        parent_run_id=parent.id if parent else None,
    )
    session.add(run)
    await session.flush()
    await create_artifact(
        session,
        event_id=event.id,
        run_id=run.id,
        step_id=None,
        artifact_type=source_artifact.artifact_type,
        name=f"edited_{source_artifact.name}",
        content=edited_content,
    )
    return await PipelineEngine(session).run(
        event, run, PipelineContext(payload=edited_content, mode=RunMode.EDIT_REPLAY, start_from_step=start_from_step)
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
    if step_name is not None and step_name not in STEP_NAMES:
        raise BadRequestError(f"Unknown step: {step_name}")
