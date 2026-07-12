from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import NotFoundError
from app.polling import repository, runner, service
from app.polling.schemas import PollingJobCreate, PollingJobPatch, PollingJobRead, PollingJobRunRead, PollingRunNowRequest

router = APIRouter(tags=["polling"])


@router.get("/api/polling/jobs", response_model=list[PollingJobRead])
@router.get("/api/polling-jobs", response_model=list[PollingJobRead])
async def list_jobs(session: AsyncSession = Depends(get_session)):
    return await repository.list_jobs(session)


@router.post("/api/polling/jobs", response_model=PollingJobRead)
@router.post("/api/polling-jobs", response_model=PollingJobRead)
async def create_job(request: PollingJobCreate, session: AsyncSession = Depends(get_session)):
    job = await service.create_job(session, request)
    await session.commit()
    return job


@router.get("/api/polling/jobs/{job_id}", response_model=PollingJobRead)
@router.get("/api/polling-jobs/{job_id}", response_model=PollingJobRead)
async def get_job(job_id: UUID, session: AsyncSession = Depends(get_session)):
    job = await repository.get_job(session, job_id)
    if job is None:
        raise NotFoundError("Polling job not found")
    return job


@router.patch("/api/polling/jobs/{job_id}", response_model=PollingJobRead)
@router.patch("/api/polling-jobs/{job_id}", response_model=PollingJobRead)
async def patch_job(job_id: UUID, request: PollingJobPatch, session: AsyncSession = Depends(get_session)):
    job = await service.patch_job(session, job_id, request)
    await session.commit()
    return job


@router.delete("/api/polling/jobs/{job_id}", status_code=204)
async def delete_job(job_id: UUID, session: AsyncSession = Depends(get_session)):
    job = await repository.get_job(session, job_id)
    if job is None:
        raise NotFoundError("Polling job not found")
    await session.delete(job)
    await session.commit()
    return Response(status_code=204)


@router.post("/api/polling/jobs/{job_id}/enable", response_model=PollingJobRead)
@router.post("/api/polling-jobs/{job_id}/enable", response_model=PollingJobRead)
async def enable_job(job_id: UUID, session: AsyncSession = Depends(get_session)):
    job = await service.set_enabled(session, job_id, True)
    await session.commit()
    return job


@router.post("/api/polling/jobs/{job_id}/disable", response_model=PollingJobRead)
@router.post("/api/polling-jobs/{job_id}/disable", response_model=PollingJobRead)
async def disable_job(job_id: UUID, session: AsyncSession = Depends(get_session)):
    job = await service.set_enabled(session, job_id, False)
    await session.commit()
    return job


@router.post("/api/polling/jobs/{job_id}/run-once", response_model=PollingJobRunRead)
async def run_job_once(job_id: UUID, request: PollingRunNowRequest | None = None, session: AsyncSession = Depends(get_session)):
    options = request or PollingRunNowRequest()
    run = await runner.run_once(session, job_id, dry_run=options.dry_run, update_cursor=options.update_cursor, allow_disabled=True)
    await session.commit()
    return run


@router.post("/api/polling-jobs/{job_id}/run-now", response_model=PollingJobRunRead)
async def run_job_now(job_id: UUID, request: PollingRunNowRequest | None = None, session: AsyncSession = Depends(get_session)):
    options = request or PollingRunNowRequest()
    run = await runner.run_once(session, job_id, dry_run=options.dry_run, update_cursor=options.update_cursor, allow_disabled=True)
    await session.commit()
    return run


@router.get("/api/polling/jobs/{job_id}/runs", response_model=list[PollingJobRunRead])
@router.get("/api/polling-jobs/{job_id}/runs", response_model=list[PollingJobRunRead])
async def list_job_runs(job_id: UUID, session: AsyncSession = Depends(get_session)):
    return await repository.list_runs(session, job_id)
