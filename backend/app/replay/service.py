from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.models import EventRun
from app.events.service import dry_run_event, edit_replay_artifact, replay_event, replay_from_run_step


async def full_replay(session: AsyncSession, event_id: UUID) -> EventRun:
    return await replay_event(session, event_id)


async def from_step(session: AsyncSession, run_id: UUID, step_name: str) -> EventRun:
    return await replay_from_run_step(session, run_id, step_name)


async def edit_and_replay(session: AsyncSession, artifact_id: UUID, edited_content: dict, start_from_step: str) -> EventRun:
    return await edit_replay_artifact(session, artifact_id, edited_content, start_from_step)


async def dry_run(session: AsyncSession, event_id: UUID) -> EventRun:
    return await dry_run_event(session, event_id)
