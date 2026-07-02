from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import PollingJobStatus
from app.core.errors import BadRequestError, NotFoundError
from app.polling.models import PollingJob
from app.polling.repository import get_job
from app.polling.schemas import PollingJobCreate, PollingJobPatch


async def create_job(session: AsyncSession, request: PollingJobCreate) -> PollingJob:
    if request.interval_seconds <= 0:
        raise BadRequestError("interval_seconds must be positive")
    now = datetime.now(timezone.utc)
    job = PollingJob(**request.model_dump(), status=PollingJobStatus.IDLE if request.enabled else PollingJobStatus.DISABLED, next_run_at=now + timedelta(seconds=request.interval_seconds))
    session.add(job)
    await session.flush()
    return job


async def patch_job(session: AsyncSession, job_id: UUID, request: PollingJobPatch) -> PollingJob:
    job = await get_job(session, job_id)
    if job is None:
        raise NotFoundError("Polling job not found")
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(job, key, value)
    if request.enabled is not None:
        job.status = PollingJobStatus.IDLE if request.enabled else PollingJobStatus.DISABLED
    await session.flush()
    return job


async def set_enabled(session: AsyncSession, job_id: UUID, enabled: bool) -> PollingJob:
    job = await get_job(session, job_id)
    if job is None:
        raise NotFoundError("Polling job not found")
    job.enabled = enabled
    job.status = PollingJobStatus.IDLE if enabled else PollingJobStatus.DISABLED
    await session.flush()
    return job
