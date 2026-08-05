from __future__ import annotations

import base64
import binascii
import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.artifacts.models import Artifact
from app.artifacts.models import content_hash as artifact_content_hash
from app.artifacts.models import content_size as artifact_content_size
from app.chz_aggregations.models import ChzAggregationRegistration
from app.chz_aggregations.schemas import (
    ChzAggregationRegistrationRequest,
    ChzAggregationSettingsPatch,
    ChzAggregationSettingsRead,
    ChzDnpPullRequest,
    ChzDnpPullResponse,
)
from app.core.config import get_settings
from app.core.enums import ArtifactType, EventStatus, RunMode, RunStatus, StepStatus
from app.core.errors import BadRequestError
from app.environments import repository as environments_repository
from app.environments.models import EnvironmentProfile, EnvironmentType, EnvironmentVariable
from app.events.models import EventRun, EventStep, IntegrationEvent

GS = "\x1d"


@dataclass(frozen=True)
class ChzAggregationRuntimeConfig:
    onec_url: str
    onec_header_name: str
    onec_token: str
    onec_timeout_seconds: float


@dataclass(frozen=True)
class ChzDnpPullRuntimeConfig:
    export_url: str
    timeout_seconds: float


@dataclass(frozen=True)
class NormalizedAggregation:
    order_number_1c: str
    order_number_external: str | None
    source_file_name: str | None
    source_system: str
    source_document_id: str | None
    rows: list[dict[str, str]]
    groups: list[dict[str, Any]]
    content_sha256: str
    duplicate_codes: int
    warnings: list[str]
    metadata_json: dict[str, Any]

    @property
    def total_codes(self) -> int:
        return len(self.rows)

    @property
    def total_aggregates(self) -> int:
        return len(self.groups)


async def read_settings(session: AsyncSession) -> ChzAggregationSettingsRead:
    config = await _runtime_config(session)
    environment = await environments_repository.current_environment(session)
    return ChzAggregationSettingsRead(
        onec_url=config.onec_url,
        header_name=config.onec_header_name,
        token_set=bool(config.onec_token),
        timeout_seconds=config.onec_timeout_seconds,
        source="current_environment" if environment else "env",
    )


async def patch_settings(session: AsyncSession, patch: ChzAggregationSettingsPatch) -> ChzAggregationSettingsRead:
    environment = await _ensure_current_environment(session)
    updates: dict[str, Any] = {}
    if patch.onec_url is not None:
        updates["CHZ_AGGREGATION_ONEC_URL"] = patch.onec_url.strip()
    if patch.onec_token is not None:
        updates["CHZ_AGGREGATION_ONEC_TOKEN"] = patch.onec_token
    if patch.onec_header_name is not None:
        updates["CHZ_AGGREGATION_ONEC_HEADER_NAME"] = patch.onec_header_name.strip() or "X-OMH-Token"
    if patch.onec_timeout_seconds is not None:
        updates["CHZ_AGGREGATION_ONEC_TIMEOUT_SECONDS"] = patch.onec_timeout_seconds
    for key, value in updates.items():
        await _upsert_environment_value(session, environment, key, value)
    await session.flush()
    session.expire(environment, ["variables"])
    return await read_settings(session)


async def preview_request(request: ChzAggregationRegistrationRequest) -> dict[str, Any]:
    normalized = _normalize_request(request)
    return _preview_response(normalized)


async def preview_file(
    content: bytes,
    *,
    file_name: str | None,
    order_number: str | None,
    source_system: str,
    source_document_id: str | None,
) -> dict[str, Any]:
    normalized = _normalize_file(
        content,
        file_name=file_name,
        order_number=order_number,
        source_system=source_system,
        source_document_id=source_document_id,
    )
    return _preview_response(normalized)


async def register_request(session: AsyncSession, request: ChzAggregationRegistrationRequest) -> tuple[ChzAggregationRegistration, dict[str, Any] | None, list[str]]:
    normalized = _normalize_request(request)
    return await _register_normalized(session, normalized)


async def register_file(
    session: AsyncSession,
    content: bytes,
    *,
    file_name: str | None,
    order_number: str | None,
    source_system: str,
    source_document_id: str | None,
) -> tuple[ChzAggregationRegistration, dict[str, Any] | None, list[str]]:
    normalized = _normalize_file(
        content,
        file_name=file_name,
        order_number=order_number,
        source_system=source_system,
        source_document_id=source_document_id,
    )
    return await _register_normalized(session, normalized)


async def pull_from_dnp(session: AsyncSession, request: ChzDnpPullRequest) -> ChzDnpPullResponse:
    config = await _dnp_pull_runtime_config(session)
    if not config.export_url:
        raise BadRequestError(
            "DnP packed codes export is not configured: set CHZ_DNP_PACKED_CODES_EXPORT_URL "
            "in the environment or as a variable of the current OMH environment"
        )
    order_number = request.order_number_1c.strip()
    payload = {
        "order_number_1c": order_number,
        "date_from": request.date_from.isoformat() if request.date_from else None,
        "date_to": request.date_to.isoformat() if request.date_to else None,
        "only_new": request.only_new,
        # The DnP side must mark rows as exported only after 1C actually consumed
        # the data, so OMH never sets mark_exported itself.
        "mark_exported": False,
    }
    event, run, step = await _start_dnp_pull_event(session, order_number, payload)
    try:
        data = await _request_dnp_packed_codes(config, payload)
        result = ChzDnpPullResponse.model_validate(data)
        if result.ok is not True:
            raise BadRequestError(f"DnP packed codes export was not successful: {str(data)[:500]}")
    except (BadRequestError, ValidationError) as exc:
        await _finish_dnp_pull_event(session, event, run, step, error=str(exc))
        await session.commit()
        if isinstance(exc, BadRequestError):
            raise
        raise BadRequestError("DnP response does not match the packed codes export contract") from exc
    await _finish_dnp_pull_event(session, event, run, step, result=result)
    result.event_id = event.id
    result.timeline_url = f"/events/{event.id}"
    return result


async def _request_dnp_packed_codes(config: ChzDnpPullRuntimeConfig, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
            response = await client.post(config.export_url, json=payload)
    except httpx.HTTPError as exc:
        raise BadRequestError(f"DnP packed codes export request failed: {exc}") from exc
    if response.status_code >= 400:
        raise BadRequestError(f"DnP rejected packed codes export with HTTP {response.status_code}: {response.text[:1000]}")
    try:
        data = response.json()
    except ValueError as exc:
        raise BadRequestError("DnP returned a non-JSON response for packed codes export") from exc
    if not isinstance(data, dict):
        raise BadRequestError("DnP returned an unexpected response shape for packed codes export")
    return data


async def _start_dnp_pull_event(session: AsyncSession, order_number: str, payload: dict[str, Any]) -> tuple[IntegrationEvent, EventRun, EventStep]:
    now = datetime.now(UTC)
    event = IntegrationEvent(
        correlation_id=f"chz-dnp-pull:{order_number}:{uuid4()}",
        source_system="1C ERP",
        target_system="DnP",
        event_type="chz.dnp_packed_codes_pull",
        entity_type="ChzDnpPackedCodesPull",
        entity_id=order_number,
        status=EventStatus.PROCESSING,
    )
    session.add(event)
    await session.flush()
    run = EventRun(event_id=event.id, run_number=1, mode=RunMode.NORMAL, status=RunStatus.RUNNING, started_at=now)
    session.add(run)
    await session.flush()
    step = EventStep(
        run_id=run.id,
        step_order=1,
        step_name="dnp_packed_codes_export",
        status=StepStatus.RUNNING,
        started_at=now,
        step_config_json={"request": payload},
    )
    session.add(step)
    await session.flush()
    return event, run, step


async def _finish_dnp_pull_event(
    session: AsyncSession,
    event: IntegrationEvent,
    run: EventRun,
    step: EventStep,
    *,
    result: ChzDnpPullResponse | None = None,
    error: str | None = None,
) -> None:
    now = datetime.now(UTC)
    step.finished_at = now
    run.finished_at = now
    if step.started_at is not None:
        step.duration_ms = int((now - step.started_at).total_seconds() * 1000)
    if error is not None:
        step.status = StepStatus.FAILED
        step.error_code = "DNP_PULL_FAILED"
        step.error_message = error[:1000]
        run.status = RunStatus.FAILED
        event.status = EventStatus.FAILED
        content: dict[str, Any] = {"error": error[:1000]}
        name = "dnp_packed_codes_export_error"
    else:
        step.status = StepStatus.SUCCESS
        run.status = RunStatus.SUCCESS
        event.status = EventStatus.SUCCESS
        tsv_sha256 = hashlib.sha256((result.tsv_text_base64 or "").encode("ascii")).hexdigest() if result else None
        # Only metadata is stored here; the marking codes themselves stay in the
        # 1C response and are not persisted as an artifact.
        content = {
            "order_number_1c": result.order_number_1c if result else None,
            "order_name_dnp": result.order_name_dnp if result else None,
            "codes_count": result.codes_count if result else None,
            "boxes_count": result.boxes_count if result else None,
            "tsv_text_base64_sha256": tsv_sha256,
        }
        name = "dnp_packed_codes_export_result"
    session.add(
        Artifact(
            event_id=event.id,
            run_id=run.id,
            step_id=step.id,
            artifact_type=ArtifactType.INCOMING_RESPONSE.value if error is None else ArtifactType.ERROR_DETAILS.value,
            name=name,
            content_json=content,
            content_hash=artifact_content_hash(content),
            size_bytes=artifact_content_size(content),
        )
    )
    await session.flush()


async def _register_normalized(
    session: AsyncSession, normalized: NormalizedAggregation
) -> tuple[ChzAggregationRegistration, dict[str, Any] | None, list[str]]:
    config = await _runtime_config(session)
    record = ChzAggregationRegistration(
        source_system=normalized.source_system,
        source_document_id=normalized.source_document_id,
        source_file_name=normalized.source_file_name,
        order_number_1c=normalized.order_number_1c,
        order_number_external=normalized.order_number_external,
        total_codes=normalized.total_codes,
        total_aggregates=normalized.total_aggregates,
        content_sha256=normalized.content_sha256,
        status="prepared",
        metadata_json={
            **normalized.metadata_json,
            "warnings": normalized.warnings,
            "duplicate_codes": normalized.duplicate_codes,
            "sample": _sample(normalized),
        },
    )
    session.add(record)
    await session.flush()

    action = await _forward_to_onec(config, record, normalized)
    if action["status"] == "success":
        record.status = "forwarded"
        record.forwarded_at = datetime.now(UTC)
        record.metadata_json = {**(record.metadata_json or {}), "onec_forward": action}
    else:
        record.status = "failed"
        record.error_message = action.get("error") or action.get("reason")
        record.metadata_json = {**(record.metadata_json or {}), "onec_forward": action}
    await session.flush()
    return record, action.get("response"), normalized.warnings


def _normalize_request(request: ChzAggregationRegistrationRequest) -> NormalizedAggregation:
    rows: list[tuple[str, str]] = []
    if request.rows:
        for row in request.rows:
            code = _code_from_sources(row.full_code or row.code, row.full_code_base64)
            rows.append((code, row.aggregate_code))
    if request.aggregates:
        for group in request.aggregates:
            if group.codes is not None:
                for code in group.codes:
                    rows.append((_normalize_code(code), group.aggregate_code))
            if group.full_codes_base64 is not None:
                for encoded in group.full_codes_base64:
                    rows.append((_decode_base64_code(encoded), group.aggregate_code))

    order_1c, order_external = _resolve_order_numbers(
        request.order_number_1c or request.order_number,
        request.order_number_external,
        request.source_file_name,
    )
    return _build_normalized(
        rows,
        order_number_1c=order_1c,
        order_number_external=order_external,
        source_file_name=request.source_file_name,
        source_system=request.source_system,
        source_document_id=request.source_document_id,
        metadata_json=request.metadata_json,
    )


def _normalize_file(
    content: bytes,
    *,
    file_name: str | None,
    order_number: str | None,
    source_system: str,
    source_document_id: str | None,
) -> NormalizedAggregation:
    if not content:
        raise BadRequestError("Aggregation file is empty")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BadRequestError("Aggregation file must be UTF-8 text") from exc

    rows: list[tuple[str, str]] = []
    for index, raw_line in enumerate(text.split("\n"), start=1):
        line = raw_line.rstrip("\r")
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            raise BadRequestError(f"Line {index} must contain exactly two tab-separated columns: code and aggregate code")
        rows.append((_normalize_code(parts[0]), _normalize_aggregate_code(parts[1], index)))
    if not rows:
        raise BadRequestError("Aggregation file does not contain code rows")

    order_1c, order_external = _resolve_order_numbers(order_number, None, file_name)
    return _build_normalized(
        rows,
        order_number_1c=order_1c,
        order_number_external=order_external,
        source_file_name=file_name,
        source_system=source_system,
        source_document_id=source_document_id,
        metadata_json={"input_format": "tab_separated_file"},
    )


def _build_normalized(
    rows: list[tuple[str, str]],
    *,
    order_number_1c: str,
    order_number_external: str | None,
    source_file_name: str | None,
    source_system: str,
    source_document_id: str | None,
    metadata_json: dict[str, Any],
) -> NormalizedAggregation:
    if not rows:
        raise BadRequestError("No aggregation rows were supplied")

    warnings: list[str] = []
    seen_codes: set[str] = set()
    duplicate_codes = 0
    normalized_rows: list[dict[str, str]] = []
    grouped: dict[str, list[str]] = {}
    for index, (code, aggregate_code) in enumerate(rows, start=1):
        if code in seen_codes:
            duplicate_codes += 1
            warnings.append(f"Duplicate marking code skipped at row {index}")
            continue
        seen_codes.add(code)
        normalized_rows.append({"code": code, "aggregate_code": aggregate_code})
        grouped.setdefault(aggregate_code, []).append(code)

    if not normalized_rows:
        raise BadRequestError("All aggregation rows are duplicates")

    groups = [
        {
            "aggregate_code": aggregate_code,
            "codes_count": len(codes),
            "full_codes_base64": [_encode_base64_code(code) for code in codes],
        }
        for aggregate_code, codes in grouped.items()
    ]
    content_hash = hashlib.sha256(_canonical_hash_payload(normalized_rows)).hexdigest()
    return NormalizedAggregation(
        order_number_1c=order_number_1c,
        order_number_external=order_number_external,
        source_file_name=source_file_name,
        source_system=source_system,
        source_document_id=source_document_id,
        rows=normalized_rows,
        groups=groups,
        content_sha256=content_hash,
        duplicate_codes=duplicate_codes,
        warnings=warnings,
        metadata_json=metadata_json,
    )


async def _forward_to_onec(config: ChzAggregationRuntimeConfig, record: ChzAggregationRegistration, normalized: NormalizedAggregation) -> dict[str, Any]:
    if not config.onec_url:
        return {"status": "failed", "reason": "CHZ_AGGREGATION_ONEC_URL is not configured"}
    payload = _onec_payload(record, normalized)
    headers = {"Content-Type": "application/json"}
    if config.onec_token:
        headers[config.onec_header_name] = config.onec_token
    try:
        async with httpx.AsyncClient(timeout=config.onec_timeout_seconds) as client:
            response = await client.post(config.onec_url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        return {"status": "failed", "url": config.onec_url, "error": f"1C request failed: {exc}"}

    if response.status_code >= 400:
        return {
            "status": "failed",
            "url": config.onec_url,
            "http_status": response.status_code,
            "error": f"1C rejected aggregation with HTTP {response.status_code}: {response.text[:1000]}",
        }
    try:
        result = response.json()
    except ValueError:
        result = {"raw_response": response.text[:1000]}
    if not isinstance(result, dict):
        result = {"response": result}
    return {"status": "success", "url": config.onec_url, "http_status": response.status_code, "response": result}


def _onec_payload(record: ChzAggregationRegistration, normalized: NormalizedAggregation) -> dict[str, Any]:
    return {
        "omh": {
            "event_id": str(record.id),
            "correlation_id": f"chz-aggregation:{normalized.order_number_1c}:{record.id}",
            "event_type": "ChestniyZnakAggregationCodesReceived",
            "entity_type": "ChzAggregationRegistration",
            "entity_id": normalized.source_document_id or normalized.order_number_1c,
            "source_system": "Open Manufacturing Hub",
            "target_system": "1C ERP",
            "sent_at": datetime.now(UTC).isoformat(),
        },
        "payload": {
            "source_system": normalized.source_system,
            "source_document_id": normalized.source_document_id,
            "source_file_name": normalized.source_file_name,
            "order_number_1c": normalized.order_number_1c,
            "order_number_external": normalized.order_number_external,
            "total_codes": normalized.total_codes,
            "total_aggregates": normalized.total_aggregates,
            "content_sha256": normalized.content_sha256,
            "aggregates": normalized.groups,
            "metadata_json": normalized.metadata_json,
        },
    }


def _preview_response(normalized: NormalizedAggregation) -> dict[str, Any]:
    return {
        "success": True,
        "status": "preview",
        "order_number_1c": normalized.order_number_1c,
        "order_number_external": normalized.order_number_external,
        "total_codes": normalized.total_codes,
        "total_aggregates": normalized.total_aggregates,
        "content_sha256": normalized.content_sha256,
        "duplicate_codes": normalized.duplicate_codes,
        "warnings": normalized.warnings,
        "sample": _sample(normalized),
    }


def _sample(normalized: NormalizedAggregation) -> dict[str, Any]:
    first_group = normalized.groups[0] if normalized.groups else {}
    first_row = normalized.rows[0] if normalized.rows else {}
    return {
        "first_aggregate_code": first_group.get("aggregate_code"),
        "first_aggregate_codes_count": first_group.get("codes_count"),
        "first_code_preview": str(first_row.get("code", "")).replace(GS, "<GS>")[:120],
    }


def _code_from_sources(code: str | None, full_code_base64: str | None) -> str:
    if full_code_base64 is not None:
        return _decode_base64_code(full_code_base64)
    return _normalize_code(code or "")


def _decode_base64_code(value: str) -> str:
    try:
        raw = base64.b64decode(str(value).strip(), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BadRequestError("Full marking code is not valid Base64") from exc
    try:
        return _normalize_code(raw.decode("ascii"))
    except UnicodeDecodeError as exc:
        raise BadRequestError("Full marking code contains non-ASCII bytes") from exc


def _encode_base64_code(code: str) -> str:
    return base64.b64encode(code.encode("ascii")).decode("ascii")


def _normalize_code(value: str) -> str:
    code = str(value).strip(" \t")
    code = code.replace("<GS>", GS).replace("{GS}", GS).replace("[GS]", GS)
    if "\n" in code or "\r" in code:
        raise BadRequestError("Marking code contains a newline")
    if not code.startswith("01"):
        raise BadRequestError("Marking code does not start with GS1 AI 01")
    try:
        code.encode("ascii")
    except UnicodeEncodeError as exc:
        raise BadRequestError("Marking code must contain only ASCII characters and GS separators") from exc
    return code


def _normalize_aggregate_code(value: str, index: int) -> str:
    aggregate_code = str(value).strip()
    if not aggregate_code:
        raise BadRequestError(f"Aggregate code at line {index} is empty")
    if "\n" in aggregate_code or "\r" in aggregate_code:
        raise BadRequestError(f"Aggregate code at line {index} contains a newline")
    return aggregate_code


def _resolve_order_numbers(order_number: str | None, order_number_external: str | None, file_name: str | None) -> tuple[str, str | None]:
    source = (order_number or "").strip()
    external = (order_number_external or "").strip() or None
    if not source and file_name:
        source = _order_from_file_name(file_name)
    if not source:
        raise BadRequestError("order_number is required or must be present in file name")
    order_1c = _order_to_1c_format(source)
    external = external or _order_to_external_format(source)
    return order_1c, external


def _order_from_file_name(file_name: str) -> str:
    match = re.search(r"(\d{2})-(\d{4})[_/-](\d{4})", file_name)
    if match:
        return f"{match.group(1)}{match.group(2)}/{match.group(3)}"
    match = re.search(r"(\d{6})[_/-](\d{4})", file_name)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    raise BadRequestError("order_number is not provided and cannot be read from file name")


def _order_to_1c_format(value: str) -> str:
    normalized = value.strip().replace("_", "/")
    match = re.fullmatch(r"(\d{2})-(\d{4})/(\d{4})", normalized)
    if match:
        return f"{match.group(1)}{match.group(2)}/{match.group(3)}"
    match = re.fullmatch(r"(\d{6})[-/](\d{4})", normalized)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    return normalized


def _order_to_external_format(value: str) -> str:
    normalized = value.strip().replace("_", "/")
    match = re.fullmatch(r"(\d{6})/(\d{4})", _order_to_1c_format(normalized))
    if match:
        return f"{match.group(1)[:2]}-{match.group(1)[2:]}/{match.group(2)}"
    return normalized


def _canonical_hash_payload(rows: list[dict[str, str]]) -> bytes:
    lines = [f"{row['code']}\t{row['aggregate_code']}" for row in rows]
    return "\n".join(lines).encode("ascii")


async def _runtime_config(session: AsyncSession) -> ChzAggregationRuntimeConfig:
    settings = get_settings()
    values = await _environment_values(session)
    return ChzAggregationRuntimeConfig(
        onec_url=_config_str(values, "CHZ_AGGREGATION_ONEC_URL", settings.chz_aggregation_onec_url),
        onec_header_name=_config_str(values, "CHZ_AGGREGATION_ONEC_HEADER_NAME", settings.chz_aggregation_onec_header_name) or "X-OMH-Token",
        onec_token=_config_str(values, "CHZ_AGGREGATION_ONEC_TOKEN", settings.chz_aggregation_onec_token),
        onec_timeout_seconds=_config_float(values, "CHZ_AGGREGATION_ONEC_TIMEOUT_SECONDS", settings.chz_aggregation_onec_timeout_seconds),
    )


async def _dnp_pull_runtime_config(session: AsyncSession) -> ChzDnpPullRuntimeConfig:
    settings = get_settings()
    values = await _environment_values(session)
    return ChzDnpPullRuntimeConfig(
        export_url=_config_str(values, "CHZ_DNP_PACKED_CODES_EXPORT_URL", settings.chz_dnp_packed_codes_export_url),
        timeout_seconds=_config_float(values, "CHZ_DNP_PACKED_CODES_TIMEOUT_SECONDS", settings.chz_dnp_packed_codes_timeout_seconds),
    )


async def _environment_values(session: AsyncSession) -> dict[str, EnvironmentVariable]:
    environment = await environments_repository.current_environment(session)
    if environment is None:
        return {}
    return {item.key: item for item in environment.variables}


async def _ensure_current_environment(session: AsyncSession) -> EnvironmentProfile:
    environment = await environments_repository.current_environment(session)
    if environment is not None:
        return environment
    environment = EnvironmentProfile(name="Production", environment_type=EnvironmentType.production, is_current=True)
    session.add(environment)
    await session.flush()
    return environment


async def _upsert_environment_value(session: AsyncSession, environment: EnvironmentProfile, key: str, value: Any) -> None:
    current = next((item for item in environment.variables if item.key == key), None)
    if current is None:
        session.add(EnvironmentVariable(environment_id=environment.id, key=key, value=str(value)))
        return
    current.value = str(value)


def _config_str(values: dict[str, EnvironmentVariable], key: str, fallback: str) -> str:
    value = values.get(key)
    if value is None:
        return fallback or ""
    return str(value.value or "")


def _config_float(values: dict[str, EnvironmentVariable], key: str, fallback: float) -> float:
    value = values.get(key)
    if value is None:
        return float(fallback)
    try:
        return float(value.value)
    except (TypeError, ValueError):
        return float(fallback)
