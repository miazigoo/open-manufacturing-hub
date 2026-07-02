from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.polling.models import PollingJob, PollingJobRun


async def list_jobs(session: AsyncSession) -> list[PollingJob]:
    result = await session.execute(select(PollingJob).order_by(PollingJob.created_at.desc()))
    return list(result.scalars().unique())


async def get_job(session: AsyncSession, job_id: UUID) -> PollingJob | None:
    return await session.get(PollingJob, job_id)


async def list_runs(session: AsyncSession, job_id: UUID) -> list[PollingJobRun]:
    result = await session.execute(select(PollingJobRun).where(PollingJobRun.job_id == job_id).order_by(PollingJobRun.started_at.desc()))
    return list(result.scalars().all())
