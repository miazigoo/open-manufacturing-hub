from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.models import ConnectorInstance
from app.connectors.registry import registry
from app.core.enums import ConnectorDirection, ConnectorInstanceStatus, PrintJobStatus, PrintLineStatus
from app.core.errors import BadRequestError, NotFoundError
from app.printing import repository
from app.printing.models import PrintJob, PrintJobLine, PrintJobLog, PrintPrinter
from app.printing.schemas import (
    ConfirmPrintedRequest,
    OneCPrintBatchRequest,
    PrintBatchLineResult,
    PrintBatchRequest,
    PrintBatchResponse,
    PrintJobCreate,
    PrintJobLineCreate,
    PrintPrinterCreate,
    PrintPrinterPatch,
    ReturnToPrintRequest,
)
from app.sdk.types import ConnectorContext


GS = "\x1d"


async def create_printer(session: AsyncSession, request: PrintPrinterCreate) -> PrintPrinter:
    connector = await _get_connector_or_404(session, request.connector_id)
    if connector.connector_type != "zpl_printer":
        raise BadRequestError("Printer must reference connector_type=zpl_printer")
    printer = PrintPrinter(
        name=request.name,
        connector_id=request.connector_id,
        dpi=request.dpi,
        enabled=request.enabled,
        description=request.description,
        settings_json=request.settings_json,
    )
    session.add(printer)
    await session.flush()
    return printer


async def patch_printer(session: AsyncSession, printer_id: UUID, request: PrintPrinterPatch) -> PrintPrinter:
    printer = await get_printer_or_404(session, printer_id)
    data = request.model_dump(exclude_unset=True)
    if "connector_id" in data:
        connector = await _get_connector_or_404(session, data["connector_id"])
        if connector.connector_type != "zpl_printer":
            raise BadRequestError("Printer must reference connector_type=zpl_printer")
    for key, value in data.items():
        setattr(printer, key, value)
    await session.flush()
    return printer


async def get_printer_or_404(session: AsyncSession, printer_id: UUID) -> PrintPrinter:
    printer = await repository.get_printer(session, printer_id)
    if printer is None:
        raise NotFoundError("Printer not found")
    return printer


async def create_job(session: AsyncSession, request: PrintJobCreate) -> PrintJob:
    existing = await repository.get_job_by_key(session, request.job_key)
    if existing is not None:
        await _ensure_same_job_payload(session, existing, request)
        return existing
    printer = await get_printer_or_404(session, request.printer_id)
    if not printer.enabled:
        raise BadRequestError("Printer is disabled")
    seen_sequences: set[int] = set()
    seen_hashes: set[str] = set()
    lines: list[PrintJobLine] = []
    for item in request.lines:
        if item.sequence_no in seen_sequences:
            raise BadRequestError(f"Duplicate sequence_no: {item.sequence_no}")
        seen_sequences.add(item.sequence_no)
        code_hash = _sha256_text(item.code)
        if code_hash in seen_hashes:
            raise BadRequestError(f"Duplicate code at sequence_no: {item.sequence_no}")
        seen_hashes.add(code_hash)
        _validate_zpl(item.zpl, item.sequence_no)
        lines.append(
            PrintJobLine(
                sequence_no=item.sequence_no,
                code=item.code,
                code_visible=item.code.replace(GS, "<GS>"),
                code_sha256=code_hash,
                zpl=item.zpl,
                zpl_sha256=_sha256_text(item.zpl),
            )
        )

    job = PrintJob(
        job_key=request.job_key,
        printer_id=request.printer_id,
        source_system=request.source_system,
        source_document_id=request.source_document_id,
        source_document_name=request.source_document_name,
        status=PrintJobStatus.READY,
        label_settings_json=request.label_settings_json,
        total_lines=len(lines),
        lines=lines,
    )
    session.add(job)
    await session.flush()
    _add_log(session, job.id, None, None, "job_created", job.status.value, f"Print job {job.job_key} created", {"total_lines": len(lines)})
    return job


async def create_and_send_onec_batch(session: AsyncSession, request: OneCPrintBatchRequest) -> PrintBatchResponse:
    printer = await _ensure_onec_printer(session, request)
    job = await create_job(
        session,
        PrintJobCreate(
            job_key=request.job_key,
            printer_id=printer.id,
            source_system=request.source_system,
            source_document_id=request.source_document_id,
            source_document_name=request.source_document_name,
            label_settings_json=request.label_settings_json,
            lines=[
                PrintJobLineCreate(sequence_no=line.sequence_no, code=line.code, zpl=line.zpl)
                for line in request.lines
            ],
        ),
    )
    limit = request.send_limit or len(request.lines)
    return await send_batch(session, job.id, PrintBatchRequest(limit=limit, dry_run=request.dry_run))


async def get_job_or_404(session: AsyncSession, job_id: UUID) -> PrintJob:
    job = await repository.get_job(session, job_id)
    if job is None:
        raise NotFoundError("Print job not found")
    return job


async def send_batch(session: AsyncSession, job_id: UUID, request: PrintBatchRequest) -> PrintBatchResponse:
    job = await get_job_or_404(session, job_id)
    printer = await get_printer_or_404(session, job.printer_id)
    if not printer.enabled:
        raise BadRequestError("Printer is disabled")
    connector = await _get_connector_or_404(session, printer.connector_id)
    if not connector.enabled or connector.status == ConnectorInstanceStatus.DISABLED:
        raise BadRequestError("Printer connector is disabled")
    if connector.status == ConnectorInstanceStatus.MAINTENANCE:
        raise BadRequestError("Printer connector is in maintenance")

    statuses = [PrintLineStatus.NEW, PrintLineStatus.ERROR]
    if request.include_returned:
        statuses.append(PrintLineStatus.RETURN_TO_PRINT)
    query = (
        select(PrintJobLine)
        .where(PrintJobLine.job_id == job.id)
        .where(PrintJobLine.status.in_(statuses))
        .order_by(PrintJobLine.sequence_no)
        .with_for_update(skip_locked=True)
        .limit(request.limit)
    )
    if request.start_sequence_no is not None:
        query = query.where(PrintJobLine.sequence_no >= request.start_sequence_no)
    result = await session.execute(query)
    lines = list(result.scalars().all())
    connector_impl = registry.get(connector.connector_type)
    now = datetime.now(timezone.utc)
    job.status = PrintJobStatus.PRINTING
    _add_log(session, job.id, None, None, "batch_started", job.status.value, "Print batch started", {"limit": request.limit, "dry_run": request.dry_run})
    await session.flush()

    line_results: list[PrintBatchLineResult] = []
    for line in lines:
        line.status = PrintLineStatus.RESERVED
        line.attempts += 1
        line.last_error = None
        _add_log(session, job.id, line.id, line.sequence_no, "line_reserved", line.status.value, "Line reserved for printing", {"attempt": line.attempts})
        await session.flush()
        payload = {"job_id": str(job.id), "line_id": str(line.id), "sequence_no": line.sequence_no, "zpl": line.zpl}
        context = ConnectorContext(
            correlation_id=job.job_key,
            source_system=job.source_system,
            target_system=connector.name,
            dry_run=request.dry_run,
            metadata={"print_job_id": str(job.id), "print_line_id": str(line.id), "sequence_no": line.sequence_no},
        )
        send_result = (
            await connector_impl.dry_run_send(connector.config_json, payload, context)
            if request.dry_run
            else await connector_impl.send(connector.config_json, payload, context)
        )
        if send_result.success:
            line.status = PrintLineStatus.TEST_MODE if request.dry_run else PrintLineStatus.SENT_TO_PRINTER
            line.sent_at = now
            _add_log(
                session,
                job.id,
                line.id,
                line.sequence_no,
                "line_sent",
                line.status.value,
                "Line sent to printer dry-run" if request.dry_run else "Line sent to printer",
                {"request": send_result.request_payload, "response": send_result.response_payload},
            )
        else:
            line.status = PrintLineStatus.ERROR
            line.last_error = send_result.error_message or send_result.error_code or "Printer send failed"
            _add_log(
                session,
                job.id,
                line.id,
                line.sequence_no,
                "line_error",
                line.status.value,
                line.last_error,
                {"error_code": send_result.error_code, "request": send_result.request_payload, "response": send_result.response_payload},
            )
        line_results.append(
            PrintBatchLineResult(
                line_id=line.id,
                sequence_no=line.sequence_no,
                status=line.status,
                success=send_result.success,
                error_code=send_result.error_code,
                error_message=send_result.error_message,
            )
        )

    await _recalculate_job(session, job)
    _add_log(session, job.id, None, None, "batch_finished", job.status.value, "Print batch finished", {"processed": len(line_results), "dry_run": request.dry_run})
    return PrintBatchResponse(
        job=job,
        processed=len(line_results),
        sent=sum(1 for item in line_results if item.success),
        failed=sum(1 for item in line_results if not item.success),
        dry_run=request.dry_run,
        results=line_results,
    )


async def confirm_printed(session: AsyncSession, job_id: UUID, request: ConfirmPrintedRequest) -> PrintJob:
    job = await get_job_or_404(session, job_id)
    query = select(PrintJobLine).where(PrintJobLine.job_id == job.id)
    if request.line_ids:
        query = query.where(PrintJobLine.id.in_(request.line_ids))
    elif request.through_sequence_no is not None:
        query = query.where(PrintJobLine.sequence_no <= request.through_sequence_no)
    else:
        raise BadRequestError("line_ids or through_sequence_no is required")
    query = query.where(PrintJobLine.status.in_([PrintLineStatus.SENT_TO_PRINTER, PrintLineStatus.TEST_MODE]))
    result = await session.execute(query)
    now = datetime.now(timezone.utc)
    for line in result.scalars().all():
        line.status = PrintLineStatus.PRINTED
        line.printed_at = now
        line.last_error = None
        _add_log(session, job.id, line.id, line.sequence_no, "line_confirmed_printed", line.status.value, "Line confirmed as printed", {})
    await _recalculate_job(session, job)
    return job


async def return_to_print(session: AsyncSession, job_id: UUID, request: ReturnToPrintRequest) -> PrintJob:
    job = await get_job_or_404(session, job_id)
    result = await session.execute(
        select(PrintJobLine)
        .where(PrintJobLine.job_id == job.id)
        .where(PrintJobLine.sequence_no >= request.from_sequence_no)
        .where(
            PrintJobLine.status.in_(
                [PrintLineStatus.SENT_TO_PRINTER, PrintLineStatus.TEST_MODE, PrintLineStatus.PRINTED, PrintLineStatus.ERROR]
            )
        )
    )
    for line in result.scalars().all():
        line.status = PrintLineStatus.RETURN_TO_PRINT
        line.last_error = request.reason
        line.printed_at = None
        _add_log(session, job.id, line.id, line.sequence_no, "line_returned_to_print", line.status.value, request.reason or "Line returned to print", {})
    await _recalculate_job(session, job)
    return job


async def _recalculate_job(session: AsyncSession, job: PrintJob) -> None:
    await session.flush()
    lines = await repository.list_job_lines(session, job.id)
    job.total_lines = len(lines)
    job.sent_lines = sum(
        1
        for line in lines
        if line.status in {PrintLineStatus.TEST_MODE, PrintLineStatus.SENT_TO_PRINTER, PrintLineStatus.PRINTED}
    )
    job.printed_lines = sum(1 for line in lines if line.status == PrintLineStatus.PRINTED)
    job.error_lines = sum(1 for line in lines if line.status == PrintLineStatus.ERROR)
    if job.error_lines:
        job.status = PrintJobStatus.ERROR
        job.last_error = next((line.last_error for line in lines if line.status == PrintLineStatus.ERROR and line.last_error), None)
    elif job.printed_lines == job.total_lines and job.total_lines:
        job.status = PrintJobStatus.PRINTED
        job.last_error = None
    elif job.sent_lines == job.total_lines and job.total_lines:
        job.status = PrintJobStatus.SENT
        job.last_error = None
    elif job.printed_lines:
        job.status = PrintJobStatus.PARTIALLY_PRINTED
        job.last_error = None
    elif job.sent_lines:
        job.status = PrintJobStatus.PARTIALLY_SENT
        job.last_error = None
    else:
        job.status = PrintJobStatus.READY
        job.last_error = None
    await session.flush()


async def _ensure_same_job_payload(session: AsyncSession, existing: PrintJob, request: PrintJobCreate) -> None:
    if existing.printer_id != request.printer_id:
        raise BadRequestError(f"Print job {request.job_key} already exists with another printer")
    existing_lines = await repository.list_job_lines(session, existing.id)
    requested = sorted((_sha256_text(item.code), item.sequence_no, _sha256_text(item.zpl)) for item in request.lines)
    current = sorted((line.code_sha256, line.sequence_no, line.zpl_sha256) for line in existing_lines)
    if current != requested:
        raise BadRequestError(f"Print job {request.job_key} already exists with different lines")


async def _get_connector_or_404(session: AsyncSession, connector_id: UUID) -> ConnectorInstance:
    connector = await session.get(ConnectorInstance, connector_id)
    if connector is None:
        raise NotFoundError("Connector not found")
    return connector


async def _ensure_onec_printer(session: AsyncSession, request: OneCPrintBatchRequest) -> PrintPrinter:
    connector_name = f"1C ZPL {request.printer.name}"
    result = await session.execute(select(ConnectorInstance).where(ConnectorInstance.name == connector_name))
    connector = result.scalar_one_or_none()
    config = {
        "printer_name": request.printer.name,
        "host": request.printer.host,
        "port": request.printer.port,
        "dpi": request.printer.dpi,
        "timeout_seconds": request.printer.timeout_seconds,
    }
    if connector is None:
        connector = ConnectorInstance(
            name=connector_name,
            connector_type="zpl_printer",
            direction=ConnectorDirection.TARGET,
            enabled=True,
            config_json=config,
            status=ConnectorInstanceStatus.ENABLED,
        )
        session.add(connector)
        await session.flush()
    else:
        connector.connector_type = "zpl_printer"
        connector.direction = ConnectorDirection.TARGET
        connector.enabled = True
        connector.status = ConnectorInstanceStatus.ENABLED
        connector.config_json = config
        await session.flush()

    printer_name = request.printer.name
    result = await session.execute(select(PrintPrinter).where(PrintPrinter.name == printer_name))
    printer = result.scalar_one_or_none()
    if printer is None:
        printer = PrintPrinter(
            name=printer_name,
            connector_id=connector.id,
            dpi=request.printer.dpi,
            enabled=True,
            settings_json={"source": "1C", "host": request.printer.host, "port": request.printer.port},
        )
        session.add(printer)
        await session.flush()
    else:
        printer.connector_id = connector.id
        printer.dpi = request.printer.dpi
        printer.enabled = True
        printer.settings_json = {"source": "1C", "host": request.printer.host, "port": request.printer.port}
        await session.flush()
    return printer


def _validate_zpl(zpl: str, sequence_no: int) -> None:
    if "^XA" not in zpl or "^XZ" not in zpl:
        raise BadRequestError(f"Line {sequence_no}: zpl must contain ^XA and ^XZ")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _add_log(
    session: AsyncSession,
    job_id: UUID,
    line_id: UUID | None,
    sequence_no: int | None,
    action: str,
    status: str,
    message: str | None,
    details: dict,
) -> None:
    session.add(
        PrintJobLog(
            job_id=job_id,
            line_id=line_id,
            sequence_no=sequence_no,
            action=action,
            status=status,
            message=message,
            details_json=details,
        )
    )
