from __future__ import annotations

import hashlib
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.marking_code_pools.models import MarkingCodePoolExport
from app.marking_code_pools.schemas import OneCMarkingCodePoolExportRequest

GS = "\x1d"


async def export_onec_pool_to_file(session: AsyncSession, request: OneCMarkingCodePoolExportRequest) -> MarkingCodePoolExport:
    codes = _normalize_codes(request.codes, request.gs_marker)
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
    return record


def _normalize_codes(codes: list[str], gs_marker: str) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for index, value in enumerate(codes, start=1):
        code = str(value).replace(gs_marker, GS)
        if "\n" in code or "\r" in code:
            raise BadRequestError(f"Code at line {index} contains a newline")
        if not code.startswith("01"):
            raise BadRequestError(f"Code at line {index} does not start with GS1 AI 01")
        if code in seen:
            raise BadRequestError(f"Duplicate code at line {index}")
        seen.add(code)
        normalized.append(code)
    return normalized


def _codes_to_file_bytes(codes: list[str]) -> bytes:
    text = "\n".join(codes)
    try:
        return text.encode("ascii")
    except UnicodeEncodeError as exc:
        raise BadRequestError("Marking codes must contain only ASCII characters and GS separators") from exc


def _default_file_name(order_number: str, total_codes: int) -> str:
    safe_order = _safe_file_part(order_number)
    return f"{safe_order}___{total_codes}_pic.txt"


def _safe_file_part(value: str) -> str:
    result = value.strip()
    for char in ('\\', '/', ':', '*', '?', '"', '<', '>', '|'):
        result = result.replace(char, "_")
    result = result.replace(" ", "_")
    return result or "unknown_order"


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
