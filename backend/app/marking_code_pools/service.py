from __future__ import annotations

import base64
import binascii
import hashlib
import os
from pathlib import Path
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import BadRequestError, NotFoundError
from app.environments import repository as environments_repository
from app.environments.models import EnvironmentProfile, EnvironmentType, EnvironmentVariable
from app.marking_code_pools import routing
from app.marking_code_pools.models import MarkingCodePoolExport, MarkingCodePoolRoutingRule
from app.marking_code_pools.schemas import (
    MarkingCodePoolActionOverrides,
    MarkingCodePoolSettingsPatch,
    MarkingCodePoolSettingsRead,
    OneCMarkingCodePoolExportRequest,
)

GS = "\x1d"


@dataclass(frozen=True)
class MarkingCodePoolRuntimeConfig:
    export_dir: str
    file_name_template: str
    allow_overwrite_default: bool
    dnp_forward_enabled: bool
    dnp_service_name: str
    dnp_url: str
    dnp_method: str
    dnp_header_name: str
    dnp_shared_secret: str
    dnp_timeout_seconds: float
    laser_file_enabled: bool
    laser_smb_unc: str
    laser_smb_username: str
    laser_smb_password: str
    laser_smb_require_signing: bool
    laser_smb_require_secure_negotiate: bool
    response_success_mode: str


@dataclass(frozen=True)
class EffectiveActionPlan:
    local_outbox: bool
    laser_file: bool
    laser_forced: bool
    laser_disabled_reason: str | None
    external_forward: bool
    external_forward_forced: bool
    external_forward_disabled_reason: str | None
    local_outbox_override_ignored: bool = False


async def export_onec_pool_to_file(
    session: AsyncSession, request: OneCMarkingCodePoolExportRequest
) -> tuple[MarkingCodePoolExport, dict | None]:
    config = await _runtime_config(session)
    action_plan = _effective_action_plan(config, request.actions_override)
    codes = _codes_from_request(request)
    rules = await routing.list_rules(session, enabled_only=True)
    segments = routing.route_codes(
        rules,
        codes,
        order_number=request.order_number,
        source_document_id=request.source_document_id,
        source_system=request.source_system,
        metadata=request.metadata_json,
    )
    if len(segments) == 1 and segments[0]["rule"] is None:
        return await _export_segment(session, config, action_plan, request, codes, rule=None, pool_group_id=None, used_file_names=set())

    pool_group_id = str(uuid4())
    used_file_names: set[str] = set()
    records: list[MarkingCodePoolExport] = []
    default_forward: dict | None = None
    for segment in segments:
        record, dnp_forward = await _export_segment(
            session, config, action_plan, request, segment["codes"],
            rule=segment["rule"], pool_group_id=pool_group_id, used_file_names=used_file_names,
        )
        records.append(record)
        if segment["rule"] is None:
            default_forward = dnp_forward
    primary = records[0]
    primary.metadata_json = {
        **(primary.metadata_json or {}),
        "segments": [_segment_metadata(record) for record in records],
        "response": _aggregate_response(records, config),
    }
    await session.flush()
    return primary, default_forward


def _segment_metadata(record: MarkingCodePoolExport) -> dict[str, Any]:
    metadata = record.metadata_json or {}
    return {
        "segment": metadata.get("segment", "default"),
        "export_id": str(record.id),
        "total_codes": record.total_codes,
        "file_name": record.file_name,
        "status": record.status,
        "error_message": record.error_message,
    }


def _aggregate_response(records: list[MarkingCodePoolExport], config: MarkingCodePoolRuntimeConfig) -> dict[str, Any]:
    responses = [(record.metadata_json or {}).get("response", {}) for record in records]
    statuses = [str(response.get("status", "failed")) for response in responses]
    if all(status in {"saved", "forwarded"} for status in statuses):
        status = "forwarded" if "forwarded" in statuses else "saved"
    elif all(status == "failed" for status in statuses):
        status = "failed"
    else:
        status = "partial_success"
    warnings: list[str] = []
    for response in responses:
        warnings.extend(str(item) for item in response.get("warnings") or [])
    return {
        "success": all(bool(response.get("success")) for response in responses),
        "status": status,
        "success_mode": config.response_success_mode,
        "warnings": warnings,
    }


async def _export_segment(
    session: AsyncSession,
    config: MarkingCodePoolRuntimeConfig,
    action_plan: EffectiveActionPlan,
    request: OneCMarkingCodePoolExportRequest,
    codes: list[str],
    *,
    rule: MarkingCodePoolRoutingRule | None,
    pool_group_id: str | None,
    used_file_names: set[str],
) -> tuple[MarkingCodePoolExport, dict | None]:
    file_name = request.file_name or _file_name_from_template(config.file_name_template, request.order_number, len(codes))
    if rule is not None:
        template = _rule_file_name_template(rule) or config.file_name_template
        file_name = _file_name_from_template(template, request.order_number, len(codes))
        stem, dot, suffix = file_name.partition(".")
        file_name = f"{stem}_{_safe_file_part(rule.name)}{dot}{suffix}"
    _validate_file_name(file_name)
    file_name = _dedupe_file_name(file_name, used_file_names)
    used_file_names.add(file_name)
    payload = _codes_to_file_bytes(codes)
    content_hash = hashlib.sha256(payload).hexdigest()
    file_path = _export_dir(config) / file_name
    request_metadata = dict(request.metadata_json or {})
    metadata_json: dict[str, Any] = {
        **request_metadata,
        "export_root": str(_export_dir(config)),
        "action_plan": _action_plan_metadata(action_plan),
    }
    if rule is not None:
        metadata_json["segment"] = f"rule:{rule.name}"
        metadata_json["routing_rule_id"] = str(rule.id)
        metadata_json["routing_targets"] = list(rule.targets_json or [])
    elif pool_group_id is not None:
        metadata_json["segment"] = "default"
    if pool_group_id is not None:
        metadata_json["pool_group_id"] = pool_group_id
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
        metadata_json=metadata_json,
    )
    session.add(record)
    await session.flush()

    allow_overwrite = config.allow_overwrite_default if request.allow_overwrite is None else request.allow_overwrite
    actions: dict[str, dict[str, Any]] = {}
    actions["local_outbox"] = _save_local_outbox(file_path, payload, allow_overwrite)
    if actions["local_outbox"].get("status") != "success":
        actions["laser_file"] = {"status": "disabled", "reason": "local_outbox failed"}
        forward_action: dict[str, Any] = {"status": "disabled", "reason": "local_outbox failed"}
        actions["external_forward"] = forward_action
        actions["dnp_forward"] = forward_action
    elif rule is None:
        actions["laser_file"] = _save_laser_file_for_plan(config, action_plan, file_name, payload)
        forward_action = await _forward_to_dnp_for_plan(config, action_plan, record, request, codes)
        actions["external_forward"] = forward_action
        actions["dnp_forward"] = forward_action
    else:
        rule_actions = await _execute_rule_targets(config, rule, record, request, codes, file_name, payload, request.actions_override)
        actions.update(rule_actions)
        forward_action = rule_actions.get("external_forward") or {"status": "disabled", "reason": "no http_forward target in rule"}
        actions.setdefault("external_forward", forward_action)
        actions["dnp_forward"] = actions["external_forward"]

    dnp_forward = forward_action.get("response") if forward_action.get("status") == "success" else None
    record.status = _overall_status(actions)
    record.error_message = _overall_error_message(actions)
    segment_plan = action_plan
    if rule is not None:
        segment_plan = EffectiveActionPlan(
            local_outbox=True,
            laser_file=actions.get("laser_file", {}).get("status") != "disabled",
            laser_forced=False,
            laser_disabled_reason=None,
            external_forward=any(key.startswith("http_forward") for key in actions),
            external_forward_forced=False,
            external_forward_disabled_reason=None,
        )
    warnings = _response_warnings(actions, segment_plan)
    response_success = _response_success(config.response_success_mode, actions, segment_plan)
    record.metadata_json = {
        **(record.metadata_json or {}),
        "actions": actions,
        "response": {
            "success": response_success,
            "status": record.status,
            "success_mode": config.response_success_mode,
            "warnings": warnings,
        },
    }
    if dnp_forward is not None:
        record.forwarded_at = datetime.now(UTC)
        record.metadata_json = {**record.metadata_json, "dnp_forward": dnp_forward}
    await session.flush()
    return record, dnp_forward


def _rule_file_name_template(rule: MarkingCodePoolRoutingRule) -> str | None:
    for target in rule.targets_json or []:
        template = target.get("file_name_template")
        if template:
            return str(template)
    return None


def _dedupe_file_name(file_name: str, used: set[str]) -> str:
    if file_name not in used:
        return file_name
    stem, dot, suffix = file_name.partition(".")
    index = 2
    while f"{stem}_{index}{dot}{suffix}" in used:
        index += 1
    return f"{stem}_{index}{dot}{suffix}"


async def _execute_rule_targets(
    config: MarkingCodePoolRuntimeConfig,
    rule: MarkingCodePoolRoutingRule,
    record: MarkingCodePoolExport,
    request: OneCMarkingCodePoolExportRequest,
    codes: list[str],
    file_name: str,
    payload: bytes,
    overrides: MarkingCodePoolActionOverrides | None,
) -> dict[str, dict[str, Any]]:
    actions: dict[str, dict[str, Any]] = {}
    targets = rule.targets_json or []
    laser_requested = any(target.get("type") == "laser_file" for target in targets)
    laser_blocked = overrides is not None and overrides.laser_file is False
    forward_blocked = overrides is not None and overrides.external_forward is False
    if laser_requested and laser_blocked:
        actions["laser_file"] = {"status": "disabled", "reason": "disabled by request actions_override"}
    elif laser_requested:
        actions["laser_file"] = _save_laser_file_if_configured(config, file_name, payload, force=True)
    else:
        actions["laser_file"] = {"status": "disabled", "reason": "no laser_file target in rule"}
    first_forward_key: str | None = None
    for target in targets:
        if target.get("type") != "http_forward":
            continue
        target_name = str(target.get("name") or target.get("url") or "http")
        key = f"http_forward:{target_name}"
        if forward_blocked:
            actions[key] = {"status": "disabled", "reason": "disabled by request actions_override", "target": target_name}
        else:
            actions[key] = await _forward_to_http_target(target, record, request, codes)
        if first_forward_key is None:
            first_forward_key = key
    if first_forward_key is not None:
        actions["external_forward"] = actions[first_forward_key]
    return actions


async def _forward_to_http_target(
    target: dict[str, Any],
    record: MarkingCodePoolExport,
    request: OneCMarkingCodePoolExportRequest,
    codes: list[str],
) -> dict[str, Any]:
    url = str(target.get("url") or "").strip()
    target_name = str(target.get("name") or url or "http_forward")
    if not url:
        return {"status": "failed", "target": target_name, "error": "http_forward target has no url"}
    timeout = float(target.get("timeout_seconds") or 600.0)
    payload = _forward_payload(record, request, codes, target_name)
    headers = {"Content-Type": "application/json"}
    token = str(target.get("token") or "")
    if token:
        headers[str(target.get("header_name") or "X-OMH-Token")] = token
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        return {"status": "failed", "target": target_name, "url": url, "error": f"{target_name} request failed: {exc}"}
    if response.status_code >= 400:
        return {
            "status": "failed",
            "target": target_name,
            "url": url,
            "http_status": response.status_code,
            "error": f"{target_name} rejected code pool with HTTP {response.status_code}: {response.text[:1000]}",
        }
    try:
        result = response.json()
    except ValueError as exc:
        return {"status": "failed", "target": target_name, "url": url, "error": f"{target_name} returned non-JSON response: {exc}"}
    if not isinstance(result, dict):
        return {"status": "failed", "target": target_name, "url": url, "error": f"{target_name} returned JSON response that is not an object"}
    return {"status": "success", "target": target_name, "url": url, "response": result}


def _forward_payload(
    record: MarkingCodePoolExport,
    request: OneCMarkingCodePoolExportRequest,
    codes: list[str],
    target_system: str,
) -> dict[str, Any]:
    return {
        "omh": {
            "event_id": str(record.id),
            "correlation_id": f"chz-code-pool:{request.order_number}:{record.id}",
            "event_type": "ChestniyZnakCodePoolPushedFrom1C",
            "entity_type": "OneCMarkingCodePool",
            "entity_id": request.source_document_id or request.order_number,
            "source_system": "Open Manufacturing Hub",
            "target_system": target_system,
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


def _codes_from_request(request: OneCMarkingCodePoolExportRequest) -> list[str]:
    if request.full_codes_base64 is not None:
        return _normalize_base64_full_codes(request.full_codes_base64)
    if request.codes is not None:
        return _normalize_codes(request.codes, request.gs_marker)
    raise BadRequestError("No marking codes were supplied")


async def preview_onec_pool_export(session: AsyncSession, request: OneCMarkingCodePoolExportRequest) -> dict[str, Any]:
    config = await _runtime_config(session)
    action_plan = _effective_action_plan(config, request.actions_override)
    codes = _codes_from_request(request)
    file_name = request.file_name or _file_name_from_template(config.file_name_template, request.order_number, len(codes))
    _validate_file_name(file_name)
    payload = _codes_to_file_bytes(codes)
    file_path = _export_dir(config) / file_name
    warnings: list[str] = []
    laser_preview = _laser_preview(config, action_plan)
    forward_preview = _forward_preview(config, action_plan)
    if laser_preview.get("requested") and not laser_preview.get("enabled") and laser_preview.get("reason"):
        warnings.append(str(laser_preview["reason"]))
    if forward_preview.get("requested") and not forward_preview.get("enabled") and forward_preview.get("reason"):
        warnings.append(str(forward_preview["reason"]))
    if action_plan.local_outbox_override_ignored:
        warnings.append("local_outbox=false ignored: local archive is required.")
    rules = await routing.list_rules(session, enabled_only=True)
    segments = routing.route_codes(
        rules,
        codes,
        order_number=request.order_number,
        source_document_id=request.source_document_id,
        source_system=request.source_system,
        metadata=request.metadata_json,
    )
    return {
        "success": True,
        "file_name": file_name,
        "total_codes": len(codes),
        "content_sha256": hashlib.sha256(payload).hexdigest(),
        "would_save_to": str(file_path),
        "would_laser_copy": laser_preview,
        "would_forward": forward_preview,
        "warnings": warnings,
        "segments": [
            {
                "segment": segment["key"],
                "rule_name": segment["rule"].name if segment["rule"] is not None else None,
                "total_codes": len(segment["codes"]),
                "targets": list(segment["rule"].targets_json) if segment["rule"] is not None else [],
            }
            for segment in segments
        ],
    }


async def read_settings(session: AsyncSession) -> MarkingCodePoolSettingsRead:
    config = await _runtime_config(session)
    environment = await environments_repository.current_environment(session)
    return MarkingCodePoolSettingsRead(
        local_outbox={
            "enabled": True,
            "required": True,
            "export_dir": config.export_dir,
            "file_name_template": config.file_name_template,
            "allow_overwrite_default": config.allow_overwrite_default,
            "note": "Локальное сохранение обязательно и используется как архив.",
        },
        laser={
            "enabled": config.laser_file_enabled,
            "smb_unc": config.laser_smb_unc,
            "username": config.laser_smb_username,
            "password_set": bool(config.laser_smb_password),
        },
        forward={
            "enabled": config.dnp_forward_enabled,
            "service_name": config.dnp_service_name,
            "url": config.dnp_url,
            "method": config.dnp_method,
            "header_name": config.dnp_header_name,
            "token_set": bool(config.dnp_shared_secret),
            "timeout_seconds": config.dnp_timeout_seconds,
        },
        response={"success_mode": config.response_success_mode},
        source="current_environment" if environment else "env",
    )


async def patch_settings(session: AsyncSession, patch: MarkingCodePoolSettingsPatch) -> MarkingCodePoolSettingsRead:
    environment = await _ensure_current_environment(session)
    updates: dict[str, Any] = {}
    if patch.export_dir is not None:
        updates["MARKING_CODE_POOL_EXPORT_DIR"] = patch.export_dir
    if patch.file_name_template is not None:
        _validate_file_name(_file_name_from_template(patch.file_name_template, "260703/5442", 2))
        updates["MARKING_CODE_POOL_FILE_NAME_TEMPLATE"] = patch.file_name_template
    if patch.allow_overwrite_default is not None:
        updates["MARKING_CODE_POOL_ALLOW_OVERWRITE_DEFAULT"] = patch.allow_overwrite_default
    if patch.laser_enabled is not None:
        updates["CHZ_LASER_FILE_ENABLED"] = patch.laser_enabled
    if patch.laser_smb_unc is not None:
        updates["CHZ_LASER_SMB_UNC"] = patch.laser_smb_unc
    if patch.laser_smb_username is not None:
        updates["CHZ_LASER_SMB_USERNAME"] = patch.laser_smb_username
    if patch.laser_smb_password is not None:
        updates["CHZ_LASER_SMB_PASSWORD"] = patch.laser_smb_password
    if patch.forward_enabled is not None:
        updates["DNP_CHZ_CODE_POOL_IMPORT_ENABLED"] = patch.forward_enabled
    if patch.forward_service_name is not None:
        updates["DNP_CHZ_CODE_POOL_SERVICE_NAME"] = patch.forward_service_name
    if patch.forward_url is not None:
        updates["DNP_CHZ_CODE_POOL_IMPORT_URL"] = patch.forward_url
    if patch.forward_method is not None:
        method = patch.forward_method.upper()
        if method != "POST":
            raise BadRequestError("Only POST is currently supported for external forward")
        updates["DNP_CHZ_CODE_POOL_IMPORT_METHOD"] = method
    if patch.forward_header_name is not None:
        updates["DNP_CHZ_CODE_POOL_HEADER_NAME"] = patch.forward_header_name or "X-OMH-Token"
    if patch.forward_token is not None:
        updates["DNP_SHARED_SECRET"] = patch.forward_token
    if patch.forward_timeout_seconds is not None:
        updates["DNP_REQUEST_TIMEOUT_SECONDS"] = patch.forward_timeout_seconds
    if patch.response_success_mode is not None:
        updates["MARKING_CODE_POOL_RESPONSE_SUCCESS_MODE"] = _normalize_success_mode(patch.response_success_mode)
    if patch.local_outbox_enabled is False:
        updates["MARKING_CODE_POOL_LOCAL_OUTBOX_ENABLED"] = True

    for key, value in updates.items():
        await _upsert_environment_value(session, environment, key, value)
    await session.flush()
    session.expire(environment, ["variables"])
    return await read_settings(session)


async def test_local_dir(session: AsyncSession) -> dict[str, Any]:
    config = await _runtime_config(session)
    directory = _export_dir(config)
    test_path = directory / f".omh-write-test-{os.getpid()}.tmp"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        _atomic_write(test_path, b"omh marking code pool write test\n")
        size = test_path.stat().st_size
    except OSError as exc:
        return {"success": False, "status": "failed", "message": str(exc), "details": {"path": str(directory)}}
    finally:
        if test_path.exists():
            test_path.unlink()
    return {
        "success": True,
        "status": "success",
        "message": "Local export directory is writable.",
        "details": {"path": str(directory), "test_size_bytes": size},
    }


async def test_laser_dir(session: AsyncSession, *, dry_run: bool = True) -> dict[str, Any]:
    config = await _runtime_config(session)
    if not config.laser_file_enabled:
        return {"success": True, "status": "disabled", "message": "SMB/laser copy is disabled.", "details": {}}
    if not config.laser_smb_unc:
        return {"success": False, "status": "failed", "message": "CHZ_LASER_SMB_UNC is not configured.", "details": {}}
    if dry_run:
        return {
            "success": True,
            "status": "dry_run",
            "message": "SMB/laser path is configured. No file was written because dry_run=true.",
            "details": {"target": config.laser_smb_unc, "username": config.laser_smb_username},
        }
    file_name = f"OMH_CHZ_WRITE_TEST_{os.getpid()}.txt"
    try:
        _write_smb_file(
            config.laser_smb_unc,
            file_name,
            b"omh marking code pool smb write test\n",
            username=config.laser_smb_username,
            password=config.laser_smb_password,
            require_signing=config.laser_smb_require_signing,
            require_secure_negotiate=config.laser_smb_require_secure_negotiate,
        )
    except Exception as exc:
        return {"success": False, "status": "failed", "message": str(exc), "details": {"target": config.laser_smb_unc}}
    return {
        "success": True,
        "status": "success",
        "message": "SMB/laser test file was written.",
        "details": {"target": config.laser_smb_unc, "file_name": file_name},
    }


async def test_forward(session: AsyncSession, *, send_test_request: bool = False) -> dict[str, Any]:
    config = await _runtime_config(session)
    if not config.dnp_forward_enabled:
        return {"success": True, "status": "disabled", "message": "External forward is disabled.", "details": {}}
    if not config.dnp_url:
        return {"success": False, "status": "failed", "message": "DNP_CHZ_CODE_POOL_IMPORT_URL is not configured.", "details": {}}
    details = {"service_name": config.dnp_service_name, "method": config.dnp_method, "url": config.dnp_url}
    if not send_test_request:
        return {
            "success": True,
            "status": "dry_run",
            "message": "External forward is configured. No HTTP request was sent.",
            "details": details,
        }
    headers = {"Content-Type": "application/json"}
    if config.dnp_shared_secret:
        headers[config.dnp_header_name] = config.dnp_shared_secret
    try:
        async with httpx.AsyncClient(timeout=config.dnp_timeout_seconds) as client:
            response = await client.post(
                config.dnp_url,
                json={"omh_test": True, "source": "marking-code-pools-settings-test", "sent_at": datetime.now(UTC).isoformat()},
                headers=headers,
            )
    except httpx.HTTPError as exc:
        return {"success": False, "status": "failed", "message": str(exc), "details": details}
    return {
        "success": response.status_code < 400,
        "status": "success" if response.status_code < 400 else "failed",
        "message": f"Forward test returned HTTP {response.status_code}.",
        "details": {**details, "http_status": response.status_code, "response_preview": response.text[:1000]},
    }


async def retry_forward(session: AsyncSession, export_id: UUID) -> dict[str, Any]:
    record = await session.get(MarkingCodePoolExport, export_id)
    if record is None:
        raise NotFoundError("Marking code pool export not found")
    config = await _runtime_config(session)
    path = _safe_export_path(record, config)
    if not path.exists() or not path.is_file():
        return {
            "success": False,
            "status": "failed",
            "message": "Export file not found on disk.",
            "error_code": "EXPORT_FILE_NOT_FOUND",
            "action": {"status": "failed", "path": str(path), "error": "Export file not found"},
        }
    try:
        codes, full_codes_base64 = _codes_from_export_file(path)
    except BadRequestError as exc:
        action = {"status": "failed", "path": str(path), "error": str(exc)}
        _store_retry_action(record, "external_forward", action)
        await session.flush()
        return {"success": False, "status": "failed", "message": str(exc), "error_code": "EXPORT_FILE_INVALID", "action": action}

    request = OneCMarkingCodePoolExportRequest(
        source_system=record.source_system,
        source_document_id=record.source_document_id,
        source_document_name=record.source_document_name,
        order_number=record.order_number,
        file_name=record.file_name,
        full_codes_base64=full_codes_base64,
        metadata_json=_business_metadata(record.metadata_json),
    )
    routing_targets = [
        target for target in (record.metadata_json or {}).get("routing_targets") or []
        if isinstance(target, dict) and target.get("type") == "http_forward"
    ]
    if routing_targets:
        last_action: dict[str, Any] = {"status": "disabled", "reason": "no http_forward target"}
        for target in routing_targets:
            last_action = await _forward_to_http_target(target, record, request, codes)
            if last_action.get("status") != "success":
                break
        action = last_action
    else:
        action = await _forward_to_dnp_if_configured(config, record, request, codes)
    _store_retry_action(record, "external_forward", action)
    if action.get("status") == "success":
        record.forwarded_at = datetime.now(UTC)
        record.metadata_json = {**(record.metadata_json or {}), "dnp_forward": action.get("response")}
    await session.flush()
    return {
        "success": action.get("status") == "success",
        "status": str(action.get("status") or "unknown"),
        "message": "External forward retry finished.",
        "error_code": None if action.get("status") == "success" else "EXTERNAL_FORWARD_FAILED",
        "action": action,
    }


async def retry_laser_copy(session: AsyncSession, export_id: UUID) -> dict[str, Any]:
    record = await session.get(MarkingCodePoolExport, export_id)
    if record is None:
        raise NotFoundError("Marking code pool export not found")
    config = await _runtime_config(session)
    path = _safe_export_path(record, config)
    if not path.exists() or not path.is_file():
        return {
            "success": False,
            "status": "failed",
            "message": "Export file not found on disk.",
            "error_code": "EXPORT_FILE_NOT_FOUND",
            "action": {"status": "failed", "path": str(path), "error": "Export file not found"},
        }
    action = _save_laser_file_if_configured(config, record.file_name, path.read_bytes())
    _store_retry_action(record, "laser_file", action)
    await session.flush()
    return {
        "success": action.get("status") == "success",
        "status": str(action.get("status") or "unknown"),
        "message": "SMB/laser copy retry finished.",
        "error_code": None if action.get("status") == "success" else "LASER_COPY_FAILED",
        "action": action,
    }


async def export_download_path(session: AsyncSession, export_id) -> tuple[Path, str]:
    record = await session.get(MarkingCodePoolExport, export_id)
    if record is None:
        raise NotFoundError("Marking code pool export not found")
    config = await _runtime_config(session)
    path = _safe_export_path(record, config)
    if not path.exists() or not path.is_file():
        raise NotFoundError("Export file not found")
    return path, record.file_name


async def _runtime_config(session: AsyncSession) -> MarkingCodePoolRuntimeConfig:
    settings = get_settings()
    values = await _current_environment_values(session)
    dnp_url = _config_str(values, "DNP_CHZ_CODE_POOL_IMPORT_URL", settings.dnp_chz_code_pool_import_url)
    explicit_forward_enabled = _config_bool_optional(values, "DNP_CHZ_CODE_POOL_IMPORT_ENABLED")
    return MarkingCodePoolRuntimeConfig(
        export_dir=_config_str(values, "MARKING_CODE_POOL_EXPORT_DIR", settings.marking_code_pool_export_dir),
        file_name_template=_config_str(
            values,
            "MARKING_CODE_POOL_FILE_NAME_TEMPLATE",
            "KM_{{order_number_safe}}___{{total_codes_formatted}}_pcs.txt",
        ),
        allow_overwrite_default=_config_bool(values, "MARKING_CODE_POOL_ALLOW_OVERWRITE_DEFAULT", True),
        dnp_forward_enabled=bool(dnp_url) if explicit_forward_enabled is None else explicit_forward_enabled,
        dnp_service_name=_config_str(values, "DNP_CHZ_CODE_POOL_SERVICE_NAME", "DnP"),
        dnp_method=_config_str(values, "DNP_CHZ_CODE_POOL_IMPORT_METHOD", "POST").upper() or "POST",
        dnp_header_name=_config_str(values, "DNP_CHZ_CODE_POOL_HEADER_NAME", "X-OMH-Token") or "X-OMH-Token",
        dnp_url=_config_str(values, "DNP_CHZ_CODE_POOL_IMPORT_URL", settings.dnp_chz_code_pool_import_url),
        dnp_shared_secret=_config_str(values, "DNP_SHARED_SECRET", settings.dnp_shared_secret),
        dnp_timeout_seconds=_config_float(values, "DNP_REQUEST_TIMEOUT_SECONDS", settings.dnp_request_timeout_seconds),
        laser_file_enabled=_config_bool(values, "CHZ_LASER_FILE_ENABLED", settings.chz_laser_file_enabled),
        laser_smb_unc=_config_str(values, "CHZ_LASER_SMB_UNC", settings.chz_laser_smb_unc),
        laser_smb_username=_config_str(values, "CHZ_LASER_SMB_USERNAME", settings.chz_laser_smb_username),
        laser_smb_password=_config_str(values, "CHZ_LASER_SMB_PASSWORD", settings.chz_laser_smb_password),
        laser_smb_require_signing=_config_bool(
            values,
            "CHZ_LASER_SMB_REQUIRE_SIGNING",
            settings.chz_laser_smb_require_signing,
        ),
        laser_smb_require_secure_negotiate=_config_bool(
            values,
            "CHZ_LASER_SMB_REQUIRE_SECURE_NEGOTIATE",
            settings.chz_laser_smb_require_secure_negotiate,
        ),
        response_success_mode=_normalize_success_mode(
            _config_str(values, "MARKING_CODE_POOL_RESPONSE_SUCCESS_MODE", "partial_success_allowed")
        ),
    )


async def _current_environment_values(session: AsyncSession) -> dict[str, Any]:
    environment = await environments_repository.current_environment(session)
    if environment is None:
        return {}
    return {item.key: item.value_json for item in environment.variables if not item.secret_ref}


async def _ensure_current_environment(session: AsyncSession) -> EnvironmentProfile:
    environment = await environments_repository.current_environment(session)
    if environment is not None:
        return environment
    environment = EnvironmentProfile(
        name="Default Environment",
        code="default",
        environment_type=EnvironmentType.DEVELOPMENT,
        description="Created automatically for CHZ marking code pool settings.",
        is_current=True,
    )
    session.add(environment)
    await session.flush()
    return environment


async def _upsert_environment_value(
    session: AsyncSession,
    environment: EnvironmentProfile,
    key: str,
    value: Any,
) -> EnvironmentVariable:
    item = await environments_repository.get_variable(session, environment.id, key)
    if item is None:
        item = EnvironmentVariable(environment_id=environment.id, key=key, value_json=value)
        session.add(item)
    else:
        item.value_json = value
        item.secret_ref = None
    await session.flush()
    return item


def _config_str(values: dict[str, Any], key: str, fallback: str) -> str:
    value = values.get(key, values.get(f"OMH_{key}", _env_value(key, fallback)))
    if value is None:
        return ""
    return str(value).strip()


def _config_float(values: dict[str, Any], key: str, fallback: float) -> float:
    value = values.get(key, values.get(f"OMH_{key}", _env_value(key, fallback)))
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _config_bool(values: dict[str, Any], key: str, fallback: bool) -> bool:
    value = values.get(key, values.get(f"OMH_{key}", _env_value(key, fallback)))
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    return str(value).strip().lower() in {"1", "true", "yes", "on", "да"}


def _config_bool_optional(values: dict[str, Any], key: str) -> bool | None:
    missing = object()
    value = values.get(key, values.get(f"OMH_{key}", _env_value(key, missing)))
    if value is missing:
        return None
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    return str(value).strip().lower() in {"1", "true", "yes", "on", "да"}


def _env_value(key: str, fallback: Any) -> Any:
    return os.getenv(key, os.getenv(f"OMH_{key}", fallback))


def _normalize_success_mode(value: str | None) -> str:
    mode = (value or "partial_success_allowed").strip()
    allowed = {"local_file_saved", "local_file_and_forward_success", "partial_success_allowed"}
    if mode not in allowed:
        raise BadRequestError("Unsupported MARKING_CODE_POOL_RESPONSE_SUCCESS_MODE")
    return mode


def _effective_action_plan(
    config: MarkingCodePoolRuntimeConfig,
    overrides: MarkingCodePoolActionOverrides | None,
) -> EffectiveActionPlan:
    local_override = overrides.local_outbox if overrides is not None else None
    laser_override = overrides.laser_file if overrides is not None else None
    forward_override = overrides.external_forward if overrides is not None else None

    if laser_override is False:
        laser_file = False
        laser_forced = False
        laser_reason = "disabled by request actions_override"
    elif laser_override is True:
        laser_file = True
        laser_forced = True
        laser_reason = None
    else:
        laser_file = config.laser_file_enabled
        laser_forced = False
        laser_reason = None if laser_file else "CHZ_LASER_FILE_ENABLED is false"

    if forward_override is False:
        external_forward = False
        forward_forced = False
        forward_reason = "disabled by request actions_override"
    elif forward_override is True:
        external_forward = True
        forward_forced = True
        forward_reason = None
    else:
        external_forward = config.dnp_forward_enabled
        forward_forced = False
        forward_reason = None if external_forward else "DNP_CHZ_CODE_POOL_IMPORT_ENABLED is false"

    return EffectiveActionPlan(
        local_outbox=True,
        laser_file=laser_file,
        laser_forced=laser_forced,
        laser_disabled_reason=laser_reason,
        external_forward=external_forward,
        external_forward_forced=forward_forced,
        external_forward_disabled_reason=forward_reason,
        local_outbox_override_ignored=local_override is False,
    )


def _action_plan_metadata(plan: EffectiveActionPlan) -> dict[str, Any]:
    return {
        "local_outbox": True,
        "laser_file": {
            "requested": plan.laser_file,
            "forced_by_request": plan.laser_forced,
            "disabled_reason": plan.laser_disabled_reason,
        },
        "external_forward": {
            "requested": plan.external_forward,
            "forced_by_request": plan.external_forward_forced,
            "disabled_reason": plan.external_forward_disabled_reason,
        },
        "local_outbox_override_ignored": plan.local_outbox_override_ignored,
    }


def _laser_preview(config: MarkingCodePoolRuntimeConfig, plan: EffectiveActionPlan) -> dict[str, Any]:
    if not plan.laser_file:
        return {
            "enabled": False,
            "requested": False,
            "target": config.laser_smb_unc,
            "reason": plan.laser_disabled_reason,
        }
    if not config.laser_smb_unc:
        return {
            "enabled": False,
            "requested": True,
            "target": "",
            "reason": "CHZ_LASER_SMB_UNC is not configured",
        }
    return {
        "enabled": True,
        "requested": True,
        "target": config.laser_smb_unc,
        "username": config.laser_smb_username,
        "forced_by_request": plan.laser_forced,
    }


def _forward_preview(config: MarkingCodePoolRuntimeConfig, plan: EffectiveActionPlan) -> dict[str, Any]:
    if not plan.external_forward:
        return {
            "enabled": False,
            "requested": False,
            "service_name": config.dnp_service_name,
            "method": config.dnp_method,
            "url": config.dnp_url,
            "reason": plan.external_forward_disabled_reason,
        }
    if not config.dnp_url:
        return {
            "enabled": False,
            "requested": True,
            "service_name": config.dnp_service_name,
            "method": config.dnp_method,
            "url": "",
            "reason": "DNP_CHZ_CODE_POOL_IMPORT_URL is not configured",
        }
    return {
        "enabled": True,
        "requested": True,
        "service_name": config.dnp_service_name,
        "method": config.dnp_method,
        "url": config.dnp_url,
        "forced_by_request": plan.external_forward_forced,
    }


def _save_laser_file_for_plan(
    config: MarkingCodePoolRuntimeConfig,
    plan: EffectiveActionPlan,
    file_name: str,
    payload: bytes,
) -> dict[str, Any]:
    if not plan.laser_file:
        return {"status": "disabled", "reason": plan.laser_disabled_reason or "laser_file is disabled"}
    return _save_laser_file_if_configured(config, file_name, payload, force=plan.laser_forced)


async def _forward_to_dnp_for_plan(
    config: MarkingCodePoolRuntimeConfig,
    plan: EffectiveActionPlan,
    record: MarkingCodePoolExport,
    request: OneCMarkingCodePoolExportRequest,
    codes: list[str],
) -> dict[str, Any]:
    if not plan.external_forward:
        return {"status": "disabled", "reason": plan.external_forward_disabled_reason or "external_forward is disabled"}
    return await _forward_to_dnp_if_configured(config, record, request, codes, force=plan.external_forward_forced)


def _response_warnings(actions: dict[str, dict[str, Any]], plan: EffectiveActionPlan) -> list[str]:
    warnings: list[str] = []
    if plan.local_outbox_override_ignored:
        warnings.append("local_outbox=false ignored because local archive is required.")
    labels = {
        "local_outbox": "Локальный архив",
        "laser_file": "Копия для лазера / SMB",
        "external_forward": "Внешняя отправка",
    }
    for key, label in labels.items():
        action = actions.get(key) or {}
        if action.get("status") == "failed" and action.get("error"):
            warnings.append(f"{label}: {action['error']}")
    return warnings


def _response_success(
    success_mode: str,
    actions: dict[str, dict[str, Any]],
    plan: EffectiveActionPlan,
) -> bool:
    if actions.get("local_outbox", {}).get("status") != "success":
        return False
    if success_mode == "local_file_and_forward_success" and plan.external_forward:
        return actions.get("external_forward", {}).get("status") == "success"
    return True


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


def _save_laser_file_if_configured(
    config: MarkingCodePoolRuntimeConfig,
    file_name: str,
    payload: bytes,
    *,
    force: bool = False,
) -> dict[str, Any]:
    if not force and not config.laser_file_enabled:
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
            require_signing=config.laser_smb_require_signing,
            require_secure_negotiate=config.laser_smb_require_secure_negotiate,
        )
    except Exception as exc:
        return {"status": "failed", "target": config.laser_smb_unc, "file_name": file_name, "error": str(exc)}
    return {"status": "success", "target": config.laser_smb_unc, "file_name": file_name}


async def _forward_to_dnp_if_configured(
    config: MarkingCodePoolRuntimeConfig,
    record: MarkingCodePoolExport,
    request: OneCMarkingCodePoolExportRequest,
    codes: list[str],
    *,
    force: bool = False,
) -> dict[str, Any]:
    if not force and not config.dnp_forward_enabled:
        return {"status": "disabled", "reason": "DNP_CHZ_CODE_POOL_IMPORT_ENABLED is false"}
    url = config.dnp_url
    if not url:
        return {"status": "disabled", "reason": "DNP_CHZ_CODE_POOL_IMPORT_URL is not configured"}

    payload = _forward_payload(record, request, codes, config.dnp_service_name)
    headers = {"Content-Type": "application/json"}
    if config.dnp_shared_secret:
        headers[config.dnp_header_name] = config.dnp_shared_secret

    timeout = _dnp_forward_timeout_seconds(config.dnp_timeout_seconds, len(codes))
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        detail = str(exc).strip() or "no details"
        return {
            "status": "failed",
            "url": url,
            "error": (
                f"DnP request timed out after {timeout:.0f}s while forwarding {len(codes)} codes "
                f"({type(exc).__name__}: {detail}). "
                "DnP may already have accepted the pool — retry-forward is idempotent."
            ),
            "timeout_seconds": timeout,
            "codes_count": len(codes),
        }
    except httpx.HTTPError as exc:
        detail = str(exc).strip() or "no details"
        return {
            "status": "failed",
            "url": url,
            "error": f"DnP request failed: {type(exc).__name__}: {detail}",
            "timeout_seconds": timeout,
            "codes_count": len(codes),
        }

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


def _dnp_forward_timeout_seconds(configured: float, codes_count: int) -> float:
    """Ensure large pools get enough time even if env still has a low legacy value.

    Empirically ~3k codes need ~2–3 minutes end-to-end through Apache/Passenger.
    Floor grows with pool size; hard cap avoids unbounded waits.
    """
    base = max(float(configured or 0.0), 600.0)
    scaled = 120.0 + max(codes_count, 0) * 0.15
    return min(max(base, scaled), 1800.0)


def _write_smb_file(
    unc_dir: str,
    file_name: str,
    payload: bytes,
    *,
    username: str,
    password: str,
    require_signing: bool,
    require_secure_negotiate: bool,
) -> None:
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
    smbclient.ClientConfig(require_secure_negotiate=require_secure_negotiate)
    smbclient.register_session(
        server,
        username=username or "guest",
        password=password or "",
        encrypt=False,
        require_signing=require_signing,
    )
    with smbclient.open_file(f"{normalized_dir}\\{file_name}", mode="wb") as file_obj:
        file_obj.write(payload)


def _overall_status(actions: dict[str, dict[str, Any]]) -> str:
    required = [actions["local_outbox"]]
    optional = [actions["laser_file"], _external_forward_action(actions)]
    if all(action["status"] == "success" for action in required + optional if action["status"] != "disabled"):
        return "forwarded" if _external_forward_action(actions)["status"] == "success" else "saved"
    if any(action["status"] == "success" for action in required + optional):
        return "partial_success"
    return "failed"


def _overall_error_message(actions: dict[str, dict[str, Any]]) -> str | None:
    seen: set[str] = set()
    errors: list[str] = []
    for name, action in actions.items():
        error = action.get("error")
        error_text = str(error) if error else ""
        if name == "dnp_forward" or action.get("status") != "failed" or not error_text or error_text in seen:
            continue
        seen.add(error_text)
        errors.append(f"{name}: {error_text}")
    return "; ".join(errors) if errors else None


def _base64_codes_for_dnp(request: OneCMarkingCodePoolExportRequest, codes: list[str]) -> list[str]:
    return [base64.b64encode(code.encode("latin-1")).decode("ascii") for code in codes]


def _external_forward_action(actions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return actions.get("external_forward") or actions.get("dnp_forward") or {"status": "disabled"}


def _safe_export_path(record: MarkingCodePoolExport, config: MarkingCodePoolRuntimeConfig) -> Path:
    path = Path(record.file_path).expanduser().resolve()
    allowed_roots = [_export_dir(config)]
    metadata_root = (record.metadata_json or {}).get("export_root")
    if metadata_root:
        allowed_roots.append(Path(str(metadata_root)).expanduser().resolve())
    for root in allowed_roots:
        try:
            path.relative_to(root)
            return path
        except ValueError:
            continue
    raise BadRequestError("Export file path is outside configured or recorded export directory")


def _codes_from_export_file(path: Path) -> tuple[list[str], list[str]]:
    lines = [line for line in path.read_bytes().splitlines() if line]
    if not lines:
        raise BadRequestError("Export file is empty")
    codes: list[str] = []
    full_codes_base64: list[str] = []
    seen: set[str] = set()
    for index, line in enumerate(lines, start=1):
        try:
            code = line.decode("ascii")
        except UnicodeDecodeError as exc:
            raise BadRequestError(f"Export file line {index} contains non-ASCII bytes") from exc
        _validate_normalized_code(code, index)
        if code in seen:
            raise BadRequestError(f"Duplicate code at line {index}")
        seen.add(code)
        codes.append(code)
        full_codes_base64.append(base64.b64encode(line).decode("ascii"))
    return codes, full_codes_base64


def _business_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    internal_keys = {"actions", "action_plan", "response", "dnp_forward", "external_forward", "export_root", "segments", "segment", "pool_group_id", "routing_rule_id", "routing_targets"}
    return {key: value for key, value in (metadata or {}).items() if key not in internal_keys}


def _store_retry_action(record: MarkingCodePoolExport, action_key: str, action: dict[str, Any]) -> None:
    metadata = dict(record.metadata_json or {})
    actions = dict(metadata.get("actions") or {})
    actions.setdefault("local_outbox", {"status": "success", "path": record.file_path})
    actions.setdefault("laser_file", {"status": "disabled", "reason": "not recorded"})
    if action_key == "external_forward":
        actions["external_forward"] = action
        actions["dnp_forward"] = action
    else:
        actions[action_key] = action
    metadata["actions"] = actions
    record.metadata_json = metadata
    record.status = _overall_status(actions)
    record.error_message = _overall_error_message(actions)


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


def _file_name_from_template(template: str, order_number: str, total_codes: int) -> str:
    value = template or "KM_{{order_number_safe}}___{{total_codes_formatted}}_pcs.txt"
    replacements = {
        "{{order_number}}": order_number,
        "{{order_number_safe}}": _safe_file_part(order_number),
        "{{total_codes}}": str(total_codes),
        "{{total_codes_formatted}}": _format_count(total_codes),
    }
    for token, replacement in replacements.items():
        value = value.replace(token, replacement)
    return value


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


def _export_dir(config: MarkingCodePoolRuntimeConfig | None = None) -> Path:
    value = config.export_dir if config is not None else get_settings().marking_code_pool_export_dir
    return Path(value).expanduser().resolve()


def _atomic_write(path: Path, payload: bytes) -> None:
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        tmp_path.write_bytes(payload)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
