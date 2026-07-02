from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.events.schemas import EventRunRead
from app.replay.schemas import EditReplayRequest, ReplayFromStepRequest
from app.events.repository import get_run_with_details
from app.replay import service

router = APIRouter(tags=["replay"])


@router.post("/api/events/{event_id}/replay", response_model=EventRunRead)
async def replay_event(event_id: UUID, session: AsyncSession = Depends(get_session)):
    run = await service.full_replay(session, event_id)
    loaded = await get_run_with_details(session, run.id)
    await session.commit()
    return loaded


@router.post("/api/runs/{run_id}/replay-from-step", response_model=EventRunRead)
async def replay_from_step(run_id: UUID, request: ReplayFromStepRequest, session: AsyncSession = Depends(get_session)):
    run = await service.from_step(session, run_id, request.step_name)
    loaded = await get_run_with_details(session, run.id)
    await session.commit()
    return loaded


@router.post("/api/artifacts/{artifact_id}/edit-replay", response_model=EventRunRead)
async def edit_replay(artifact_id: UUID, request: EditReplayRequest, session: AsyncSession = Depends(get_session)):
    run = await service.edit_and_replay(session, artifact_id, request.edited_content, request.start_from_step)
    loaded = await get_run_with_details(session, run.id)
    await session.commit()
    return loaded


@router.post("/api/events/{event_id}/dry-run", response_model=EventRunRead)
async def dry_run(event_id: UUID, session: AsyncSession = Depends(get_session)):
    run = await service.dry_run(session, event_id)
    loaded = await get_run_with_details(session, run.id)
    await session.commit()
    return loaded
