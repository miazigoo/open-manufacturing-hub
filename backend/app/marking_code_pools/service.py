from __future__ import annotations

import base64
import binascii
import hashlib
import os
from pathlib import Path
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import BadRequestError
from app.environments import repository as environments_repository
from app.marking_code_pools.models import MarkingCodePoolExport
from app.marking_code_pools.schemas import OneCMarkingCodePoolExportRequest

GS = "\x1d"


@dataclass(frozen=True)
class MarkingCodePoolRuntimeConfig:
    dnp_url: str
    dnp_shared_secret: str
    dnp_timeout_seconds: float
    laser_file_enabled: bool
    laser_smb_unc: str
    laser_smb_username: str
    laser_smb_password: str


async def export_onec_pool_to_file(
    session: AsyncSession, request: OneCMarkingCodePoolExportRequest
) -> tuple[MarkingCodePoolExport, dict | None]:
    codes = _codes_from_request(request)
    file_name = request.file_name or _default_file_name(request.order_number, len(codes))
    _validate_file_name(file_name)
    payload = _codes_to_file_bytes(codes)
    content_hash = hashlib.sha256(payload).hexdigest()
    file_path = _export_dir() / file_name
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

    config = await _runtime_config(session)
    actions: dict[str, dict[str, Any]] = {}
    actions["local_outbox"] = _save_local_outbox(file_path, payload, request.allow_overwrite)
    actions["laser_file"] = _save_laser_file_if_configured(config, file_name, payload)
    actions["dnp_forward"] = await _forward_to_dnp_if_configured(config, record, request, codes)

    dnp_forward = actions["dnp_forward"].get("response") if actions["dnp_forward"].get("status") == "success" else None
    record.status = _overall_status(actions)
    record.error_message = _overall_error_message(actions)
    record.metadata_json = {**(record.metadata_json or {}), "actions": actions}
    if dnp_forward is not None:
        record.forwarded_at = datetime.now(UTC)
        record.metadata_json = {**record.metadata_json, "dnp_forward": dnp_forward}
    await session.flush()
    return record, dnp_forward


def _codes_from_request(request: OneCMarkingCodePoolExportRequest) -> list[str]:
    if request.full_codes_base64 is not None:
        return _normalize_base64_full_codes(request.full_codes_base64)
    if request.codes is not None:
        return _normalize_codes(request.codes, request.gs_marker)
    raise BadRequestError("No marking codes were supplied")


async def _runtime_config(session: AsyncSession) -> MarkingCodePoolRuntimeConfig:
    settings = get_settings()
    values = await _current_environment_values(session)
    return MarkingCodePoolRuntimeConfig(
        dnp_url=_config_str(values, "DNP_CHZ_CODE_POOL_IMPORT_URL", settings.dnp_chz_code_pool_import_url),
        dnp_shared_secret=_config_str(values, "DNP_SHARED_SECRET", settings.dnp_shared_secret),
        dnp_timeout_seconds=_config_float(values, "DNP_REQUEST_TIMEOUT_SECONDS", settings.dnp_request_timeout_seconds),
        laser_file_enabled=_config_bool(values, "CHZ_LASER_FILE_ENABLED", settings.chz_laser_file_enabled),
        laser_smb_unc=_config_str(values, "CHZ_LASER_SMB_UNC", settings.chz_laser_smb_unc),
        laser_smb_username=_config_str(values, "CHZ_LASER_SMB_USERNAME", settings.chz_laser_smb_username),
        laser_smb_password=_config_str(values, "CHZ_LASER_SMB_PASSWORD", settings.chz_laser_smb_password),
    )


async def _current_environment_values(session: AsyncSession) -> dict[str, Any]:
    environment = await environments_repository.current_environment(session)
    if environment is None:
        return {}
    return {item.key: item.value_json for item in environment.variables if not item.secret_ref}


def _config_str(values: dict[str, Any], key: str, fallback: str) -> str:
    value = values.get(key, values.get(f"OMH_{key}", fallback))
    if value is None:
        return ""
    return str(value).strip()


def _config_float(values: dict[str, Any], key: str, fallback: float) -> float:
    value = values.get(key, values.get(f"OMH_{key}", fallback))
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _config_bool(values: dict[str, Any], key: str, fallback: bool) -> bool:
    value = values.get(key, values.get(f"OMH_{key}", fallback))
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    return str(value).strip().lower() in {"1", "true", "yes", "on", "да"}


def _save_local_outbox(file_path: Path, payload: bytes, allow_overwrite: bool) -> dict[str, Any]:
    try:
        export_dir = file_path.parent
        export_dir.mkdir(parents=True, exist_ok=True)
        if file_path.exists() and not allow_overwrite:
            return {"status": "failed", "path": str(file_path), "error": f"Export file already exists: {file_path.name}"}
        _atomic_write(file_path, payload)
    except OSError as exc:
        return {"status": "failed", "path": str(file_path), "error": str(exc)}
    return {"status": "success", "path": str(file_path)}


def _save_laser_file_if_configured(config: MarkingCodePoolRuntimeConfig, file_name: str, payload: bytes) -> dict[str, Any]:
    if not config.laser_file_enabled:
        return {"status": "disabled", "reason": "CHZ_LASER_FILE_ENABLED is false"}
    if not config.laser_smb_unc:
        return {"status": "disabled", "reason": "CHZ_LASER_SMB_UNC is not configured"}
    try:
        _write_smb_file(
            config.laser_smb_unc,
            file_name,
            payload,
            username=config.laser_smb_username,
            password=config.laser_smb_password,
        )
    except Exception as exc:
        return {"status": "failed", "target": config.laser_smb_unc, "file_name": file_name, "error": str(exc)}
    return {"status": "success", "target": config.laser_smb_unc, "file_name": file_name}


async def _forward_to_dnp_if_configured(
    config: MarkingCodePoolRuntimeConfig,
    record: MarkingCodePoolExport,
    request: OneCMarkingCodePoolExportRequest,
    codes: list[str],
) -> dict[str, Any]:
    url = config.dnp_url
    if not url:
        return {"status": "disabled", "reason": "DNP_CHZ_CODE_POOL_IMPORT_URL is not configured"}

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
    if config.dnp_shared_secret:
        headers["X-OMH-Token"] = config.dnp_shared_secret

    try:
        async with httpx.AsyncClient(timeout=config.dnp_timeout_seconds) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        return {"status": "failed", "url": url, "error": f"DnP request failed: {exc}"}

    if response.status_code >= 400:
        return {
            "status": "failed",
            "url": url,
            "http_status": response.status_code,
            "error": f"DnP rejected code pool with HTTP {response.status_code}: {response.text[:1000]}",
        }

    try:
        result = response.json()
    except ValueError as exc:
        return {"status": "failed", "url": url, "error": f"DnP returned non-JSON response: {exc}"}

    if not isinstance(result, dict):
        return {"status": "failed", "url": url, "error": "DnP returned JSON response that is not an object"}

    return {"status": "success", "url": url, "response": result}


def _write_smb_file(unc_dir: str, file_name: str, payload: bytes, *, username: str, password: str) -> None:
    try:
        import smbclient
    except ImportError as exc:
        raise RuntimeError("smbprotocol is not installed, cannot write to SMB share") from exc

    normalized_dir = unc_dir.replace("/", "\\").rstrip("\\")
    if not normalized_dir.startswith("\\\\"):
        raise ValueError("CHZ_LASER_SMB_UNC must look like \\\\server\\share")
    parts = normalized_dir.strip("\\").split("\\", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("CHZ_LASER_SMB_UNC must include server and share")
    server = parts[0]
    smbclient.register_session(server, username=username or "guest", password=password or "")
    with smbclient.open_file(f"{normalized_dir}\\{file_name}", mode="wb") as file_obj:
        file_obj.write(payload)


def _overall_status(actions: dict[str, dict[str, Any]]) -> str:
    required = [actions["local_outbox"]]
    optional = [actions["laser_file"], actions["dnp_forward"]]
    if all(action["status"] == "success" for action in required + optional if action["status"] != "disabled"):
        return "forwarded" if actions["dnp_forward"]["status"] == "success" else "saved"
    if any(action["status"] == "success" for action in required + optional):
        return "partial_success"
    return "failed"


def _overall_error_message(actions: dict[str, dict[str, Any]]) -> str | None:
    errors = [
        f"{name}: {action['error']}"
        for name, action in actions.items()
        if action.get("status") == "failed" and action.get("error")
    ]
    return "; ".join(errors) if errors else None


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
