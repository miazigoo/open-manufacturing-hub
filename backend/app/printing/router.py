from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errors import NotFoundError
from app.printing import repository, service
from app.printing.schemas import (
    CancelPrintJobRequest,
    CancelPrintJobResponse,
    ConfirmPrintedRequest,
    OneCPrintBatchRequest,
    PrintBatchRequest,
    PrintBatchResponse,
    PrintJobCreate,
    PrintJobLineRead,
    PrintJobLogRead,
    PrintJobRead,
    PrintPrinterCreate,
    PrintPrinterPatch,
    PrintPrinterRead,
    ReturnToPrintRequest,
)

router = APIRouter(tags=["printing"])


@router.get("/api/printing/printers", response_model=list[PrintPrinterRead])
async def list_printers(session: AsyncSession = Depends(get_session)):
    return await repository.list_printers(session)


@router.post("/api/printing/printers", response_model=PrintPrinterRead)
async def create_printer(request: PrintPrinterCreate, session: AsyncSession = Depends(get_session)):
    printer = await service.create_printer(session, request)
    await session.commit()
    return printer


@router.patch("/api/printing/printers/{printer_id}", response_model=PrintPrinterRead)
async def patch_printer(printer_id: UUID, request: PrintPrinterPatch, session: AsyncSession = Depends(get_session)):
    printer = await service.patch_printer(session, printer_id, request)
    await session.commit()
    return printer


@router.delete("/api/printing/printers/{printer_id}", status_code=204)
async def delete_printer(printer_id: UUID, session: AsyncSession = Depends(get_session)):
    printer = await repository.get_printer(session, printer_id)
    if printer is None:
        raise NotFoundError("Printer not found")
    await session.delete(printer)
    await session.commit()
    return Response(status_code=204)


@router.get("/api/printing/jobs", response_model=list[PrintJobRead])
async def list_jobs(session: AsyncSession = Depends(get_session)):
    return await repository.list_jobs(session)


@router.post("/api/printing/jobs", response_model=PrintJobRead)
async def create_job(request: PrintJobCreate, session: AsyncSession = Depends(get_session)):
    job = await service.create_job(session, request)
    await session.commit()
    return job


@router.post("/api/printing/onec/send-batch", response_model=PrintBatchResponse)
async def create_and_send_onec_batch(request: OneCPrintBatchRequest, session: AsyncSession = Depends(get_session)):
    result = await service.create_and_send_onec_batch(session, request)
    await session.commit()
    return result


@router.get("/api/printing/jobs/{job_id}", response_model=PrintJobRead)
async def get_job(job_id: UUID, session: AsyncSession = Depends(get_session)):
    return await service.get_job_or_404(session, job_id)


@router.get("/api/printing/jobs/{job_id}/lines", response_model=list[PrintJobLineRead])
async def list_job_lines(
    job_id: UUID,
    limit: int | None = None,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    job = await service.get_job_or_404(session, job_id)
    return await repository.list_job_lines(session, job.id, limit=limit, offset=offset)


@router.get("/api/printing/jobs/{job_id}/logs", response_model=list[PrintJobLogRead])
async def list_job_logs(job_id: UUID, session: AsyncSession = Depends(get_session)):
    job = await service.get_job_or_404(session, job_id)
    return await repository.list_job_logs(session, job.id)


@router.post("/api/printing/jobs/{job_id}/send-batch", response_model=PrintBatchResponse)
async def send_batch(job_id: UUID, request: PrintBatchRequest, session: AsyncSession = Depends(get_session)):
    result = await service.send_batch(session, job_id, request)
    await session.commit()
    return result


@router.post("/api/printing/jobs/{job_id}/cancel", response_model=CancelPrintJobResponse)
async def cancel_print_job(job_id: UUID, request: CancelPrintJobRequest, session: AsyncSession = Depends(get_session)):
    result = await service.cancel_print_job(session, job_id, request)
    await session.commit()
    return result


@router.post("/api/printing/jobs/{job_id}/confirm-printed", response_model=PrintJobRead)
async def confirm_printed(job_id: UUID, request: ConfirmPrintedRequest, session: AsyncSession = Depends(get_session)):
    job = await service.confirm_printed(session, job_id, request)
    await session.commit()
    return job


@router.post("/api/printing/jobs/{job_id}/return-to-print", response_model=PrintJobRead)
async def return_to_print(job_id: UUID, request: ReturnToPrintRequest, session: AsyncSession = Depends(get_session)):
    job = await service.return_to_print(session, job_id, request)
    await session.commit()
    return job
