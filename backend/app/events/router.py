from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.enums import EventStatus
from app.events import service
from app.events.schemas import (
    EventCreate,
    EventDashboardSummary,
    EventJournalItem,
    EventJournalPageResponse,
    EventOverview,
    EventRunSummary,
    EventSummary,
    EventTimeline,
)

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


@router.get("/journal/page", response_model=EventJournalPageResponse)
async def list_event_journal_page(
    status: EventStatus | None = Query(None),
    event_type: str | None = Query(None),
    source: str | None = Query(None),
    target: str | None = Query(None),
    q: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
):
    return await service.get_event_journal_page(
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


@router.get("/dashboard-summary", response_model=EventDashboardSummary)
async def get_dashboard_summary(session: AsyncSession = Depends(get_session)):
    return await service.get_dashboard_summary(session)


@router.get("/{event_id}", response_model=EventSummary)
async def get_event(event_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_event_or_404(session, event_id)


@router.get("/{event_id}/overview", response_model=EventOverview)
async def get_overview(
    event_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    brief: bool = False,
    before_run: int | None = Query(default=None, ge=1),
    session: AsyncSession = Depends(get_session),
):
    return await service.get_event_overview(session, event_id, limit, offset, brief=brief, before_run=before_run)


@router.get("/{event_id}/runs/{run_id}/metadata", response_model=EventRunSummary)
async def run_metadata(event_id: UUID, run_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.run_metadata(session, event_id, run_id)


@router.get("/{event_id}/timeline", response_model=EventTimeline)
async def get_timeline(event_id: UUID, session: AsyncSession = Depends(get_session)):
    event = await service.get_timeline_or_404(session, event_id)
    queue_item = await service.queue_info_for_event(session, event_id)
    return {"event": event, "runs": event.runs, "queue_item": queue_item}


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
