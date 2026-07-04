from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.events import service
from app.events.schemas import EventCreate, EventJournalItem, EventSummary, EventTimeline

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("", response_model=EventSummary)
async def create_event(request: EventCreate, session: AsyncSession = Depends(get_session)):
    event = await service.create_event(session, request)
    await session.commit()
    return event


@router.get("", response_model=list[EventSummary])
async def list_events(session: AsyncSession = Depends(get_session)):
    return await service.get_events(session)


@router.get("/journal", response_model=list[EventJournalItem])
async def list_event_journal(session: AsyncSession = Depends(get_session)):
    return await service.get_event_journal(session)


@router.get("/{event_id}", response_model=EventSummary)
async def get_event(event_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_event_or_404(session, event_id)


@router.get("/{event_id}/timeline", response_model=EventTimeline)
async def get_timeline(event_id: UUID, session: AsyncSession = Depends(get_session)):
    event = await service.get_timeline_or_404(session, event_id)
    return {"event": event, "runs": event.runs}


@router.post("/{event_id}/pin", response_model=EventSummary)
async def pin_event(event_id: UUID, session: AsyncSession = Depends(get_session)):
    event = await service.set_pinned(session, event_id, True)
    await session.commit()
    return event


@router.post("/{event_id}/unpin", response_model=EventSummary)
async def unpin_event(event_id: UUID, session: AsyncSession = Depends(get_session)):
    event = await service.set_pinned(session, event_id, False)
    await session.commit()
    return event
