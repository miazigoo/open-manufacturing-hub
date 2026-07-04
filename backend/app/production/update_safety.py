from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.production.models import ProductionState


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def state(session: AsyncSession) -> ProductionState:
    item = await session.get(ProductionState, "default")
    if item is None:
        item = ProductionState(id="default")
        session.add(item)
        await session.flush()
    return item


async def enable(session: AsyncSession, *, message: str | None = None, enabled_by: str | None = None) -> ProductionState:
    item = await state(session)
    item.update_mode_enabled = True
    item.update_mode_message = message or "Update mode enabled. New requests are queued but not processed."
    item.update_mode_enabled_at = utcnow()
    item.update_mode_enabled_by = enabled_by
    await session.flush()
    return item


async def disable(session: AsyncSession) -> ProductionState:
    item = await state(session)
    item.update_mode_enabled = False
    item.update_mode_message = None
    item.update_mode_enabled_at = None
    item.update_mode_enabled_by = None
    await session.flush()
    return item


async def is_enabled(session: AsyncSession) -> bool:
    return (await state(session)).update_mode_enabled


def as_status(item: ProductionState) -> dict:
    return {"enabled": item.update_mode_enabled, "message": item.update_mode_message, "enabled_at": item.update_mode_enabled_at, "enabled_by": item.update_mode_enabled_by}
