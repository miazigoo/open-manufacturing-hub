from __future__ import annotations

import base64
import binascii
import hashlib
import os
from pathlib import Path
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.marking_code_pools.models import MarkingCodePoolExport
from app.marking_code_pools.schemas import OneCMarkingCodePoolExportRequest

GS = "\x1d"


async def export_onec_pool_to_file(
    session: AsyncSession, request: OneCMarkingCodePoolExportRequest
) -> tuple[MarkingCodePoolExport, dict | None]:
    codes = _codes_from_request(request)
    file_name = request.file_name or _default_file_name(request.order_number, len(codes))
    _validate_file_name(file_name)
    payload = _codes_to_file_bytes(codes)
    content_hash = hashlib.sha256(payload).hexdigest()
    export_dir = _export_dir()
    export_dir.mkdir(parents=True, exist_ok=True)
    file_path = export_dir / file_name
    if file_path.exists() and not request.allow_overwrite:
        raise BadRequestError(f"Export file already exists: {file_name}")
    _atomic_write(file_path, payload)
    record = MarkingCodePoolExport(
        source_system=request.source_system,
        source_document_id=request.source_document_id,
        source_document_name=request.source_document_name,
        order_number=request.order_number,
        file_name=file_name,
        file_path=str(file_path),
        total_codes=len(codes),
        content_sha256=content_hash,
        status="saved",
        metadata_json=request.metadata_json,
    )
    session.add(record)
    await session.flush()
    dnp_forward = await _forward_to_dnp_if_configured(record, request, codes)
    if dnp_forward is not None:
        record.status = "forwarded"
        record.forwarded_at = datetime.now(UTC)
        record.metadata_json = {**(record.metadata_json or {}), "dnp_forward": dnp_forward}
        await session.flush()
    return record, dnp_forward


def _codes_from_request(request: OneCMarkingCodePoolExportRequest) -> list[str]:
    if request.full_codes_base64 is not None:
        return _normalize_base64_full_codes(request.full_codes_base64)
    if request.codes is not None:
        return _normalize_codes(request.codes, request.gs_marker)
    raise BadRequestError("No marking codes were supplied")


async def _forward_to_dnp_if_configured(
    record: MarkingCodePoolExport,
    request: OneCMarkingCodePoolExportRequest,
    codes: list[str],
) -> dict | None:
    settings = get_settings()
    url = settings.dnp_chz_code_pool_import_url.strip()
    if not url:
        return None

    payload = {
        "omh": {
            "event_id": str(record.id),
            "correlation_id": f"chz-code-pool:{request.order_number}:{record.id}",
            "event_type": "ChestniyZnakCodePoolPushedFrom1C",
            "entity_type": "OneCMarkingCodePool",
            "entity_id": request.source_document_id or request.order_number,
            "source_system": "Open Manufacturing Hub",
            "target_system": "DnP",
            "sent_at": datetime.now(UTC).isoformat(),
        },
        "payload": {
            "source_system": request.source_system,
            "source_document_id": request.source_document_id,
            "source_document_name": request.source_document_name,
            "order_number": request.order_number,
            "file_name": record.file_name,
            "total_codes": record.total_codes,
            "content_sha256": record.content_sha256,
            "full_codes_base64": _base64_codes_for_dnp(request, codes),
            "metadata_json": request.metadata_json,
        },
    }
    headers = {"Content-Type": "application/json"}
    if settings.dnp_shared_secret:
        headers["X-OMH-Token"] = settings.dnp_shared_secret

    try:
        async with httpx.AsyncClient(timeout=settings.dnp_request_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        record.status = "forward_failed"
        record.error_message = f"DnP request failed: {exc}"
        raise BadRequestError(record.error_message) from exc

    if response.status_code >= 400:
        record.status = "forward_failed"
        record.error_message = f"DnP rejected code pool with HTTP {response.status_code}: {response.text[:1000]}"
        raise BadRequestError(record.error_message)

    try:
        result = response.json()
    except ValueError as exc:
        record.status = "forward_failed"
        record.error_message = "DnP returned non-JSON response"
        raise BadRequestError(record.error_message) from exc

    if not isinstance(result, dict):
        record.status = "forward_failed"
        record.error_message = "DnP returned JSON response that is not an object"
        raise BadRequestError(record.error_message)

    return result


def _base64_codes_for_dnp(request: OneCMarkingCodePoolExportRequest, codes: list[str]) -> list[str]:
    if request.full_codes_base64 is not None:
        return [str(value).strip() for value in request.full_codes_base64]
    return [base64.b64encode(code.encode("latin-1")).decode("ascii") for code in codes]


def _normalize_base64_full_codes(full_codes_base64: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for index, value in enumerate(full_codes_base64, start=1):
        encoded = str(value).strip()
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise BadRequestError(f"Full marking code at line {index} is not valid Base64") from exc
        try:
            code = raw.decode("ascii")
        except UnicodeDecodeError as exc:
            raise BadRequestError(f"Full marking code at line {index} contains non-ASCII bytes") from exc
        _validate_normalized_code(code, index)
        if code in seen:
            raise BadRequestError(f"Duplicate code at line {index}")
        seen.add(code)
        normalized.append(code)
    return normalized


def _normalize_codes(codes: list[str], gs_marker: str) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for index, value in enumerate(codes, start=1):
        code = str(value).replace(gs_marker, GS)
        _validate_normalized_code(code, index)
        if code in seen:
            raise BadRequestError(f"Duplicate code at line {index}")
        seen.add(code)
        normalized.append(code)
    return normalized


def _validate_normalized_code(code: str, index: int) -> None:
    if "\n" in code or "\r" in code:
        raise BadRequestError(f"Code at line {index} contains a newline")
    if not code.startswith("01"):
        raise BadRequestError(f"Code at line {index} does not start with GS1 AI 01")


def _codes_to_file_bytes(codes: list[str]) -> bytes:
    text = "\n".join(codes)
    try:
        return text.encode("ascii")
    except UnicodeEncodeError as exc:
        raise BadRequestError("Marking codes must contain only ASCII characters and GS separators") from exc


def _default_file_name(order_number: str, total_codes: int) -> str:
    safe_order = _safe_file_part(order_number)
    return f"KM_{safe_order}___{_format_count(total_codes)}_pcs.txt"


def _safe_file_part(value: str) -> str:
    result = value.strip()
    result = result.replace("/", "-")
    for char in ('\\', ':', '*', '?', '"', '<', '>', '|'):
        result = result.replace(char, "_")
    result = result.replace(" ", "_")
    return result or "unknown_order"


def _format_count(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def _validate_file_name(file_name: str) -> None:
    if Path(file_name).name != file_name:
        raise BadRequestError("file_name must not contain path separators")
    if not file_name.lower().endswith(".txt"):
        raise BadRequestError("file_name must end with .txt")
    if any(char in file_name for char in ('\\', '/', ':', '*', '?', '"', '<', '>', '|')):
        raise BadRequestError("file_name contains unsupported characters")


def _export_dir() -> Path:
    return Path(get_settings().marking_code_pool_export_dir).expanduser().resolve()


def _atomic_write(path: Path, payload: bytes) -> None:
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp_path.write_bytes(payload)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
