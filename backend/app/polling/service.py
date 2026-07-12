import re
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
    if request.schedule_type not in {"manual_only", "interval_minutes"}:
        raise BadRequestError("schedule_type must be manual_only or interval_minutes")
    now = datetime.now(timezone.utc)
    data = request.model_dump()
    data["slug"] = data.get("slug") or _slugify(request.name)
    next_run_at = now + timedelta(seconds=request.interval_seconds) if request.enabled and request.schedule_type == "interval_minutes" else None
    job = PollingJob(**data, status=PollingJobStatus.IDLE if request.enabled else PollingJobStatus.DISABLED, next_run_at=next_run_at)
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
    if request.schedule_type is not None and request.schedule_type not in {"manual_only", "interval_minutes"}:
        raise BadRequestError("schedule_type must be manual_only or interval_minutes")
    if job.enabled and job.schedule_type == "interval_minutes" and job.next_run_at is None:
        job.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=job.interval_seconds)
    if job.schedule_type == "manual_only":
        job.next_run_at = None
    await session.flush()
    return job


async def set_enabled(session: AsyncSession, job_id: UUID, enabled: bool) -> PollingJob:
    job = await get_job(session, job_id)
    if job is None:
        raise NotFoundError("Polling job not found")
    job.enabled = enabled
    job.status = PollingJobStatus.IDLE if enabled else PollingJobStatus.DISABLED
    job.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=job.interval_seconds) if enabled and job.schedule_type == "interval_minutes" else None
    await session.flush()
    return job


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-_")
    return slug or "polling-job"
