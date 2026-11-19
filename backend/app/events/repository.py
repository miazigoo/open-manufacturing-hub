from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import lazyload, selectinload

from app.core.enums import EventStatus
from app.core.pagination import decode_cursor, encode_cursor
from app.events.models import EventRun, EventStep, IntegrationEvent


def _escape_like(val: str) -> str:
    return val.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


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


async def list_events(session: AsyncSession, limit: int = 200) -> list[IntegrationEvent]:
    # runs/artifacts are selectin-eager on the model and artifact JSONB payloads are
    # heavy, so list views explicitly skip them and cap the page size.
    result = await session.execute(
        select(IntegrationEvent)
        .options(lazyload(IntegrationEvent.runs), lazyload(IntegrationEvent.artifacts))
        .order_by(IntegrationEvent.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_events_page(
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
) -> tuple[list[IntegrationEvent], str | None, bool]:
    conditions = []

    if status is not None:
        conditions.append(IntegrationEvent.status == status)

    if event_type is not None and event_type.strip():
        conditions.append(IntegrationEvent.event_type.ilike(f"%{_escape_like(event_type.strip())}%", escape="\\"))

    if source is not None and source.strip():
        conditions.append(IntegrationEvent.source_system.ilike(f"%{_escape_like(source.strip())}%", escape="\\"))

    if target is not None and target.strip():
        conditions.append(IntegrationEvent.target_system.ilike(f"%{_escape_like(target.strip())}%", escape="\\"))

    if date_from is not None:
        conditions.append(IntegrationEvent.created_at >= date_from)

    if date_to is not None:
        conditions.append(IntegrationEvent.created_at < date_to)

    if q is not None and q.strip():
        cleaned_q = q.strip()
        q_uuid: UUID | None = None
        try:
            q_uuid = UUID(cleaned_q)
        except (ValueError, AttributeError):
            pass

        escaped_q = _escape_like(cleaned_q)
        q_or = [
            IntegrationEvent.entity_id.ilike(f"%{escaped_q}%", escape="\\"),
            IntegrationEvent.correlation_id.ilike(f"%{escaped_q}%", escape="\\"),
        ]
        if q_uuid is not None:
            q_or.append(IntegrationEvent.id == q_uuid)
        conditions.append(or_(*q_or))

    if cursor:
        cursor_ts, cursor_id = decode_cursor(cursor)
        conditions.append(
            or_(
                IntegrationEvent.created_at < cursor_ts,
                and_(
                    IntegrationEvent.created_at == cursor_ts,
                    IntegrationEvent.id < cursor_id,
                ),
            )
        )

    stmt = (
        select(IntegrationEvent)
        .options(lazyload(IntegrationEvent.runs), lazyload(IntegrationEvent.artifacts))
        .order_by(IntegrationEvent.created_at.desc(), IntegrationEvent.id.desc())
        .limit(limit + 1)
    )

    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = await session.execute(stmt)
    rows = list(result.scalars().all())

    if len(rows) > limit:
        has_more = True
        items = rows[:limit]
        next_cursor = encode_cursor(items[-1].created_at, items[-1].id)
    else:
        has_more = False
        items = rows
        next_cursor = None

    return items, next_cursor, has_more


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
