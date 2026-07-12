from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.connection_center import service as connection_center_service
from app.connection_center.schemas import ConnectionProfileRead
from app.core.errors import BadRequestError, NotFoundError
from app.data_contracts.models import DataContract
from app.operation_catalog.models import OperationProfile
from app.operation_catalog.presets import OPERATION_PRESETS
from app.operation_catalog.schemas import InstallPresetsResponse, OperationCatalogOptions, OperationKind, OperationProfileCreate, OperationProfileOption, OperationProfilePatch, OperationProfileRead
from app.packages.runtime import is_package_enabled

ALLOWED_KINDS = {"rest_api_operation", "onec_http_operation", "printer_operation", "file_operation", "training_operation"}
HTTP_KINDS = {"rest_api_operation", "onec_http_operation", "training_operation"}
ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}
ALLOWED_BODY_TYPES = {"json", "xml", "raw_text", "form", "none"}
KIND_CONNECTIONS = {
    "rest_api_operation": {"rest_api", "training_mock"},
    "onec_http_operation": {"onec_http_service"},
    "printer_operation": {"printer"},
    "file_operation": {"smb_share", "local_directory"},
    "training_operation": {"training_mock", "rest_api", "onec_http_service"},
}
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,179}$")


async def list_operations(session: AsyncSession, *, kind: OperationKind | None = None, connection_profile_id: UUID | None = None) -> list[OperationProfileRead]:
    stmt = select(OperationProfile).order_by(OperationProfile.name.asc())
    if kind:
        stmt = stmt.where(OperationProfile.kind == kind)
    if connection_profile_id:
        stmt = stmt.where(OperationProfile.connection_profile_id == connection_profile_id)
    rows = list((await session.execute(stmt)).scalars().all())
    profiles = await _connection_profiles_by_connector(session)
    return [_read_from_model(row, _matching_connection(row, profiles)) for row in rows]


async def create_operation(session: AsyncSession, payload: OperationProfileCreate) -> OperationProfileRead:
    data = _normalize_data(payload.model_dump())
    await _validate_data(session, data)
    row = OperationProfile(**data)
    session.add(row)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise BadRequestError("Операция с таким code уже существует. Выберите уникальный код.") from exc
    profiles = await _connection_profiles_by_connector(session)
    return _read_from_model(row, _matching_connection(row, profiles))


async def get_operation_or_404(session: AsyncSession, operation_id: UUID) -> OperationProfile:
    row = await session.get(OperationProfile, operation_id)
    if row is None:
        raise NotFoundError("Operation profile not found")
    return row


async def get_operation(session: AsyncSession, operation_id: UUID) -> OperationProfileRead:
    row = await get_operation_or_404(session, operation_id)
    profiles = await _connection_profiles_by_connector(session)
    return _read_from_model(row, _matching_connection(row, profiles))


async def patch_operation(session: AsyncSession, operation_id: UUID, payload: OperationProfilePatch) -> OperationProfileRead:
    row = await get_operation_or_404(session, operation_id)
    data = _normalize_data(payload.model_dump(exclude_unset=True), current=row)
    await _validate_data(session, data, current=row)
    for key, value in data.items():
        setattr(row, key, value)
    try:
        await session.flush()
    except IntegrityError as exc:
        raise BadRequestError("Операция с таким code уже существует. Выберите уникальный код.") from exc
    profiles = await _connection_profiles_by_connector(session)
    return _read_from_model(row, _matching_connection(row, profiles))


async def delete_operation(session: AsyncSession, operation_id: UUID) -> None:
    row = await get_operation_or_404(session, operation_id)
    await session.delete(row)
    await session.flush()


async def set_enabled(session: AsyncSession, operation_id: UUID, enabled: bool) -> OperationProfileRead:
    row = await get_operation_or_404(session, operation_id)
    row.enabled = enabled
    await session.flush()
    profiles = await _connection_profiles_by_connector(session)
    return _read_from_model(row, _matching_connection(row, profiles))


async def options(session: AsyncSession, *, kinds: set[str] | None = None, include_disabled: bool = False) -> list[OperationProfileOption]:
    stmt = select(OperationProfile).order_by(OperationProfile.name.asc())
    if kinds:
        stmt = stmt.where(OperationProfile.kind.in_(kinds))
    rows = list((await session.execute(stmt)).scalars().all())
    profiles = await _connection_profiles_by_connector(session)
    result: list[OperationProfileOption] = []
    for row in rows:
        if not include_disabled and not row.enabled:
            continue
        if row.package_id and not await is_package_enabled(session, row.package_id):
            continue
        connection = _matching_connection(row, profiles)
        if row.connection_profile_id and connection is None:
            continue
        if connection and not include_disabled and not connection.enabled:
            continue
        result.append(_option_from_model(row, connection))
    return result


async def options_bundle(session: AsyncSession) -> OperationCatalogOptions:
    operations = await options(session)
    grouped: dict[str, list[OperationProfileOption]] = {kind: [] for kind in sorted(ALLOWED_KINDS)}
    for operation in operations:
        grouped.setdefault(operation.kind, []).append(operation)
    return OperationCatalogOptions(operations=operations, by_kind=grouped)


async def install_presets(session: AsyncSession) -> InstallPresetsResponse:
    connections = await connection_center_service.options(session, include_disabled=False)
    rest_connection = next((item.connector_id for item in connections if item.kind in {"rest_api", "training_mock"}), None)
    onec_connection = next((item.connector_id for item in connections if item.kind == "onec_http_service"), None)
    installed: list[OperationProfileRead] = []
    skipped: list[str] = []
    for preset in OPERATION_PRESETS:
        connection_id = rest_connection if preset["kind"] == "rest_api_operation" else onec_connection if preset["kind"] == "onec_http_operation" else None
        if connection_id is None and not preset.get("full_url"):
            skipped.append(f"{preset['code']}: нет подходящего Connection Profile")
            continue
        result = await session.execute(select(OperationProfile).where(OperationProfile.code == preset["code"]))
        row = result.scalar_one_or_none()
        data = {**preset, "connection_profile_id": connection_id, "enabled": True}
        await _validate_data(session, data, current=row)
        if row is None:
            row = OperationProfile(**data)
            session.add(row)
        else:
            for key, value in data.items():
                setattr(row, key, value)
        await session.flush()
        profiles = await _connection_profiles_by_connector(session)
        installed.append(_read_from_model(row, _matching_connection(row, profiles)))
    return InstallPresetsResponse(installed=installed, skipped=skipped)


async def connection_for_operation(session: AsyncSession, operation: OperationProfile) -> ConnectionProfileRead | None:
    profiles = await _connection_profiles_by_connector(session)
    return _matching_connection(operation, profiles)


def final_url(operation: OperationProfile, connection: ConnectionProfileRead | None = None) -> str | None:
    full_url = _clean(operation.full_url)
    if full_url:
        return full_url
    path = _clean(operation.path)
    if path and path.startswith(("http://", "https://", "/api/")) and connection is None:
        return path
    base = _connection_base_url(connection)
    if base and path:
        return _join_url(base, path)
    if base and not path:
        return base
    return path


def _read_from_model(row: OperationProfile, connection: ConnectionProfileRead | None) -> OperationProfileRead:
    return OperationProfileRead(
        id=row.id,
        name=row.name,
        code=row.code,
        kind=row.kind,  # type: ignore[arg-type]
        connection_profile_id=row.connection_profile_id,
        request_contract_id=row.request_contract_id,
        response_contract_id=row.response_contract_id,
        connection_name=connection.name if connection else None,
        connection_kind=connection.kind if connection else None,
        description=row.description,
        enabled=row.enabled,
        method=row.method,  # type: ignore[arg-type]
        path=row.path,
        full_url=row.full_url,
        final_url=final_url(row, connection),
        headers_json=row.headers_json,
        body_type=row.body_type,  # type: ignore[arg-type]
        request_template_json=row.request_template_json,
        request_template_text=row.request_template_text,
        response_body_type=row.response_body_type,  # type: ignore[arg-type]
        success_condition_json=row.success_condition_json,
        response_extractors_json=row.response_extractors_json,
        sample_request_json=row.sample_request_json,
        sample_response_json=row.sample_response_json,
        timeout_seconds=row.timeout_seconds,
        tags_json=row.tags_json,
        package_id=row.package_id,
        used_by=_used_by(row),
        last_test_at=row.last_test_at,
        last_test_success=row.last_test_success,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _option_from_model(row: OperationProfile, connection: ConnectionProfileRead | None) -> OperationProfileOption:
    return OperationProfileOption(
        id=row.id,
        label=row.name,
        name=row.name,
        code=row.code,
        kind=row.kind,  # type: ignore[arg-type]
        connection_profile_id=row.connection_profile_id,
        request_contract_id=row.request_contract_id,
        response_contract_id=row.response_contract_id,
        connection_name=connection.name if connection else None,
        connection_kind=connection.kind if connection else None,
        method=row.method,
        path=row.path,
        full_url=row.full_url,
        final_url=final_url(row, connection),
        headers_json=row.headers_json,
        body_type=row.body_type,
        response_body_type=row.response_body_type,
        timeout_seconds=row.timeout_seconds,
        tags=row.tags_json or [],
        used_by=_used_by(row),
    )


def _normalize_data(data: dict[str, Any], current: OperationProfile | None = None) -> dict[str, Any]:
    normalized = dict(data)
    if "code" in normalized and isinstance(normalized["code"], str):
        normalized["code"] = _slug(normalized["code"])
    if "name" in normalized and isinstance(normalized["name"], str):
        normalized["name"] = normalized["name"].strip()
    if "method" in normalized and isinstance(normalized["method"], str):
        normalized["method"] = normalized["method"].strip().upper() or None
    for key in ["path", "full_url", "description", "body_type", "response_body_type", "package_id", "request_template_text"]:
        if key in normalized and isinstance(normalized[key], str):
            normalized[key] = normalized[key].strip() or None
    if "tags_json" in normalized and normalized["tags_json"] is not None:
        normalized["tags_json"] = [str(item).strip() for item in normalized["tags_json"] if str(item).strip()]
    if "headers_json" in normalized and normalized["headers_json"] is None and current is None:
        normalized["headers_json"] = {}
    return normalized


async def _validate_data(session: AsyncSession, data: dict[str, Any], current: OperationProfile | None = None) -> None:
    merged = _current_dict(current)
    merged.update(data)
    code = str(merged.get("code") or "").strip()
    if not code or not SLUG_RE.match(code):
        raise BadRequestError("Code должен начинаться с латинской буквы/цифры и содержать только a-z, 0-9, '.', '_' или '-'.")
    kind = str(merged.get("kind") or "")
    if kind not in ALLOWED_KINDS:
        raise BadRequestError("Неподдерживаемый тип операции подключения.")
    method = merged.get("method")
    if kind in HTTP_KINDS:
        if not method:
            raise BadRequestError("Для REST API и 1C HTTP операций укажите HTTP method.")
        if str(method).upper() not in ALLOWED_METHODS:
            raise BadRequestError("HTTP method должен быть одним из GET, POST, PUT, PATCH, DELETE.")
        path = _clean(merged.get("path"))
        full_url = _clean(merged.get("full_url"))
        if not path and not full_url:
            raise BadRequestError("Укажите path внутри подключения или full_url для manual endpoint.")
        if path and not path.startswith(("/", "http://", "https://")):
            raise BadRequestError("Path операции должен начинаться с '/' или быть полным URL.")
    body_type = merged.get("body_type")
    if body_type and body_type not in ALLOWED_BODY_TYPES:
        raise BadRequestError("body_type должен быть json, xml, raw_text, form или none.")
    response_body_type = merged.get("response_body_type")
    if response_body_type and response_body_type not in ALLOWED_BODY_TYPES:
        raise BadRequestError("response_body_type должен быть json, xml, raw_text, form или none.")
    headers = merged.get("headers_json")
    if headers is not None and not isinstance(headers, dict):
        raise BadRequestError("headers_json должен быть JSON object.")
    _validate_success_condition(merged.get("success_condition_json"))
    _validate_extractors(merged.get("response_extractors_json"))
    connection_id = merged.get("connection_profile_id")
    if connection_id:
        profiles = await _connection_profiles_by_connector(session)
        connection = _matching_connection_data(str(kind), connection_id, profiles)
        if connection is None:
            expected = ", ".join(sorted(KIND_CONNECTIONS.get(kind, set())))
            raise BadRequestError(f"Операция {kind} должна ссылаться на Connection Profile типа: {expected}.")
    for key, label in [("request_contract_id", "request contract"), ("response_contract_id", "response contract")]:
        contract_id = merged.get(key)
        if contract_id and await session.get(DataContract, contract_id) is None:
            raise BadRequestError(f"{label} ссылается на несуществующий Data Contract.")


def _validate_success_condition(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        raise BadRequestError("success_condition_json должен быть объектом вида {mode, conditions}.")
    mode = value.get("mode", "all")
    if mode not in {"all", "any"}:
        raise BadRequestError("success_condition_json.mode должен быть all или any.")
    conditions = value.get("conditions")
    if not isinstance(conditions, list):
        raise BadRequestError("success_condition_json.conditions должен быть массивом условий.")
    allowed = {"http_status_2xx", "http_status_equals", "json_path_equals", "json_path_exists", "response_contains_text", "always_success"}
    for condition in conditions:
        if not isinstance(condition, dict) or condition.get("type") not in allowed:
            raise BadRequestError("Условие успеха должно иметь поддерживаемый type.")


def _validate_extractors(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, list):
        raise BadRequestError("response_extractors_json должен быть массивом extractors.")
    for item in value:
        if not isinstance(item, dict) or not item.get("name") or not item.get("path"):
            raise BadRequestError("Каждый response extractor должен иметь name и path.")


def _current_dict(row: OperationProfile | None) -> dict[str, Any]:
    if row is None:
        return {}
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


async def _connection_profiles_by_connector(session: AsyncSession) -> dict[UUID, list[ConnectionProfileRead]]:
    result: dict[UUID, list[ConnectionProfileRead]] = {}
    for profile in await connection_center_service.list_profiles(session):
        result.setdefault(profile.connector_id, []).append(profile)
    return result


def _matching_connection(row: OperationProfile, profiles: dict[UUID, list[ConnectionProfileRead]]) -> ConnectionProfileRead | None:
    if not row.connection_profile_id:
        return None
    return _matching_connection_data(row.kind, row.connection_profile_id, profiles)


def _matching_connection_data(kind: str, connection_id: UUID | str, profiles: dict[UUID, list[ConnectionProfileRead]]) -> ConnectionProfileRead | None:
    try:
        lookup = UUID(str(connection_id))
    except ValueError:
        return None
    allowed = KIND_CONNECTIONS.get(kind, set())
    for profile in profiles.get(lookup, []):
        if profile.kind in allowed:
            return profile
    return None


def _connection_base_url(connection: ConnectionProfileRead | None) -> str | None:
    if connection is None:
        return None
    config = connection.config_json or {}
    if connection.kind == "onec_http_service":
        return _clean(config.get("http_service_base_url") or config.get("base_url") or config.get("url"))
    if connection.kind in {"rest_api", "training_mock"}:
        return _clean(config.get("url") or config.get("base_url"))
    if connection.kind == "printer":
        return _clean(config.get("url")) or (f"tcp://{config.get('host')}:{config.get('port') or 9100}" if config.get("host") else None)
    return _clean(config.get("unc_path") or config.get("path"))


def _join_url(base: str, path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


def _used_by(row: OperationProfile) -> list[str]:
    tags = set(row.tags_json or [])
    used: list[str] = []
    if row.kind == "rest_api_operation":
        used.extend(["Request -> OData -> Send Endpoint", "Poll OData -> Send Target"])
    if row.kind == "onec_http_operation":
        used.extend(["WMS -> 1C", "Source -> Web API -> Write Back to 1C", "XML Raw Bridge"])
    if "chz" in tags or "dnp" in tags:
        used.append("CHZ Code Pool Workbench")
    if row.kind == "printer_operation":
        used.append("Request -> Print")
    if row.kind == "file_operation":
        used.append("CHZ Code Pool Workbench")
    return used


def _slug(value: str) -> str:
    slug = value.strip().lower().replace(" ", "_")
    slug = re.sub(r"[^a-z0-9_.-]+", "_", slug)
    return slug.strip("_.-") or "operation"


def _clean(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None
