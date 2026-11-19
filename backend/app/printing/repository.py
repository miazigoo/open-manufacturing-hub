from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.printing.models import PrintJob, PrintJobLine, PrintJobLog, PrintPrinter


async def list_printers(session: AsyncSession) -> list[PrintPrinter]:
    result = await session.execute(select(PrintPrinter).order_by(PrintPrinter.name))
    return list(result.scalars().all())


async def get_printer(session: AsyncSession, printer_id: UUID) -> PrintPrinter | None:
    return await session.get(PrintPrinter, printer_id)


async def list_jobs(session: AsyncSession) -> list[PrintJob]:
    result = await session.execute(select(PrintJob).order_by(PrintJob.created_at.desc()))
    return list(result.scalars().all())


async def get_job(session: AsyncSession, job_id: UUID) -> PrintJob | None:
    return await session.get(PrintJob, job_id)


async def get_job_by_key(session: AsyncSession, job_key: str) -> PrintJob | None:
    result = await session.execute(select(PrintJob).where(PrintJob.job_key == job_key))
    return result.scalar_one_or_none()


async def list_job_lines(
    session: AsyncSession,
    job_id: UUID,
    limit: int | None = None,
    offset: int = 0,
) -> list[PrintJobLine]:
    stmt = select(PrintJobLine).where(PrintJobLine.job_id == job_id).order_by(PrintJobLine.sequence_no)
    if offset > 0:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_job_logs(session: AsyncSession, job_id: UUID) -> list[PrintJobLog]:
    result = await session.execute(select(PrintJobLog).where(PrintJobLog.job_id == job_id).order_by(PrintJobLog.created_at.desc()))
    return list(result.scalars().all())
