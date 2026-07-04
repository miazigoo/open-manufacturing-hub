from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.enterprise_runtime import service as queue_service


async def process_once(session: AsyncSession, worker: str = "queue-worker"):
    return await queue_service.process_once(session, worker=worker)


async def process_batch(session: AsyncSession, limit: int = 10, worker: str = "queue-worker"):
    return await queue_service.process_batch(session, limit=limit, worker=worker)
