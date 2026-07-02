from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.events.models import EventRun, EventStep, IntegrationEvent


async def get_event(session: AsyncSession, event_id: UUID) -> IntegrationEvent | None:
    return await session.get(IntegrationEvent, event_id)


async def get_event_with_timeline(session: AsyncSession, event_id: UUID) -> IntegrationEvent | None:
    result = await session.execute(
        select(IntegrationEvent)
        .where(IntegrationEvent.id == event_id)
        .options(
            selectinload(IntegrationEvent.runs).selectinload(EventRun.steps).selectinload(EventStep.artifacts),
            selectinload(IntegrationEvent.runs).selectinload(EventRun.artifacts),
        )
    )
    return result.scalar_one_or_none()


async def list_events(session: AsyncSession) -> list[IntegrationEvent]:
    result = await session.execute(select(IntegrationEvent).order_by(IntegrationEvent.created_at.desc()))
    return list(result.scalars().all())


async def latest_run(session: AsyncSession, event_id: UUID) -> EventRun | None:
    result = await session.execute(
        select(EventRun).where(EventRun.event_id == event_id).order_by(EventRun.run_number.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def next_run_number(session: AsyncSession, event_id: UUID) -> int:
    result = await session.execute(select(func.max(EventRun.run_number)).where(EventRun.event_id == event_id))
    return (result.scalar_one() or 0) + 1

async def get_run_with_details(session: AsyncSession, run_id: UUID) -> EventRun | None:
    result = await session.execute(
        select(EventRun)
        .where(EventRun.id == run_id)
        .options(selectinload(EventRun.steps).selectinload(EventStep.artifacts), selectinload(EventRun.artifacts))
    )
    run = result.scalar_one_or_none()
    if run is not None:
        run.steps.sort(key=lambda step: step.step_order)
    return run
