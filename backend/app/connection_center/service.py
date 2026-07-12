from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import repository as connector_repository
from app.connectors import service as connector_service
from app.connectors.models import ConnectorInstance
from app.connectors.schemas import ConnectorInstanceCreate, ConnectorInstancePatch
from app.connection_center.migration import connector_profile_kinds, is_training_connector
from app.connection_center.schemas import ConnectionCenterOptions, ConnectionProfileCreate, ConnectionProfileKind, ConnectionProfileOption, ConnectionProfilePatch, ConnectionProfileRead, ConnectionProfileHealth, SecretReferenceRead
from app.core.enums import ConnectorDirection
from app.core.errors import BadRequestError, NotFoundError
from app.secrets.redaction import collect_secret_references, mask_config, raw_secret_warnings

PROFILE_KINDS: set[str] = {"onec_odata", "onec_http_service", "rest_api", "printer", "smb_share", "local_directory", "training_mock"}


def profile_id(kind: str, connector_id: UUID | str) -> str:
    return f"{kind}:{connector_id}"


async def list_profiles(session: AsyncSession, kind: ConnectionProfileKind | None = None) -> list[ConnectionProfileRead]:
    profiles: list[ConnectionProfileRead] = []
    for connector in await connector_repository.list_instances(session):
        for connector_kind in connector_profile_kinds(connector):
            if kind and connector_kind != kind:
                continue
            profiles.append(_profile_from_connector(connector, connector_kind))
    return profiles


async def get_profile(session: AsyncSession, profile_ref: str) -> ConnectionProfileRead:
    connector, kind = await _get_connector_and_kind(session, profile_ref)
    return _profile_from_connector(connector, kind)


async def create_profile(session: AsyncSession, payload: ConnectionProfileCreate) -> ConnectionProfileRead:
    connector_type, direction, config = _connector_payload_from_profile(payload)
    connector = await connector_service.create_instance(
        session,
        ConnectorInstanceCreate(
            name=payload.name,
            connector_type=connector_type,
            direction=direction,
            enabled=payload.enabled,
            config_json=config,
        ),
    )
    return _profile_from_connector(connector, payload.kind)


async def patch_profile(session: AsyncSession, profile_ref: str, payload: ConnectionProfilePatch) -> ConnectionProfileRead:
    connector, kind = await _get_connector_and_kind(session, profile_ref)
    data = payload.model_dump(exclude_unset=True)
    patch_data: dict[str, Any] = {}
    if "name" in data:
        patch_data["name"] = data["name"]
    if "enabled" in data:
        patch_data["enabled"] = data["enabled"]
    if "config_json" in data or "description" in data or "tags" in data:
        config = _merge_config(connector.config_json or {}, data.get("config_json") or {})
        omh = config.get("omh") if isinstance(config.get("omh"), dict) else {}
        if "description" in data:
            omh["description"] = data["description"]
        if "tags" in data:
            omh["tags"] = data["tags"] or []
        omh["connection_profile_kind"] = kind
        config["omh"] = omh
        patch_data["config_json"] = config
    if not patch_data:
        return _profile_from_connector(connector, kind)
    connector = await connector_service.patch_instance(session, connector.id, ConnectorInstancePatch(**patch_data))
    return _profile_from_connector(connector, kind)


async def delete_profile(session: AsyncSession, profile_ref: str) -> ConnectorInstance:
    connector, kind = await _get_connector_and_kind(session, profile_ref)
    kinds = connector_profile_kinds(connector)
    if len(kinds) > 1 and kind in kinds:
        config = dict(connector.config_json or {})
        if kind == "onec_odata":
            odata = config.get("odata") if isinstance(config.get("odata"), dict) else {}
            config["odata"] = {**odata, "enabled": False}
        elif kind == "onec_http_service":
            http_services = config.get("http_services") if isinstance(config.get("http_services"), dict) else {}
            config["http_services"] = {**http_services, "enabled": False}
            config.pop("http_service_base_url", None)
        else:
            raise BadRequestError("Cannot partially delete this multi-kind connector profile")
        await connector_service.patch_instance(session, connector.id, ConnectorInstancePatch(config_json=config))
        return connector
    await session.delete(connector)
    await session.flush()
    return connector


async def set_enabled(session: AsyncSession, profile_ref: str, enabled: bool) -> ConnectionProfileRead:
    connector, kind = await _get_connector_and_kind(session, profile_ref)
    connector = await connector_service.set_enabled(session, connector.id, enabled)
    return _profile_from_connector(connector, kind)


async def options(session: AsyncSession, kinds: set[ConnectionProfileKind] | None = None, include_disabled: bool = False) -> list[ConnectionProfileOption]:
    result: list[ConnectionProfileOption] = []
    for profile in await list_profiles(session):
        if kinds and profile.kind not in kinds:
            continue
        if not include_disabled and not profile.enabled:
            continue
        result.append(_option_from_profile(profile))
    return result


async def options_bundle(session: AsyncSession) -> ConnectionCenterOptions:
    all_options = await options(session)
    grouped: dict[str, list[ConnectionProfileOption]] = {kind: [] for kind in sorted(PROFILE_KINDS)}
    for option in all_options:
        grouped.setdefault(option.kind, []).append(option)
    return ConnectionCenterOptions(profiles=all_options, by_kind=grouped)


async def get_connector_for_test(session: AsyncSession, profile_ref: str) -> tuple[ConnectorInstance, ConnectionProfileKind, str]:
    connector, kind = await _get_connector_and_kind(session, profile_ref)
    return connector, kind, profile_id(kind, connector.id)


def _profile_from_connector(connector: ConnectorInstance, kind: str) -> ConnectionProfileRead:
    if kind not in PROFILE_KINDS:
        raise BadRequestError(f"Unsupported connection profile kind: {kind}")
    config = connector.config_json or {}
    omh = config.get("omh") if isinstance(config.get("omh"), dict) else {}
    tags = omh.get("tags") if isinstance(omh.get("tags"), list) else []
    description = omh.get("description") if isinstance(omh.get("description"), str) else config.get("description") if isinstance(config.get("description"), str) else None
    refs = [SecretReferenceRead(name=name, path=path) for name, path in collect_secret_references(config)]
    warnings = raw_secret_warnings(config)
    return ConnectionProfileRead(
        id=profile_id(kind, connector.id),
        connector_id=connector.id,
        name=connector.name,
        kind=kind,  # type: ignore[arg-type]
        description=description,
        enabled=connector.enabled,
        status=connector.status.value if hasattr(connector.status, "value") else str(connector.status),
        training=is_training_connector(connector),
        package_id=_package_id(kind),
        config_json=mask_config(config),
        secret_refs=refs,
        warnings=warnings,
        tags=[str(tag) for tag in tags],
        health=ConnectionProfileHealth(status=connector.last_health_status, message=connector.last_health_message, checked_at=connector.last_health_at),
        used_by=_used_by(kind),
        read_only=False,
        created_at=connector.created_at,
        updated_at=connector.updated_at,
    )


def _option_from_profile(profile: ConnectionProfileRead) -> ConnectionProfileOption:
    return ConnectionProfileOption(
        id=str(profile.connector_id),
        profile_id=profile.id,
        connector_id=profile.connector_id,
        label=profile.name,
        name=profile.name,
        kind=profile.kind,
        enabled=profile.enabled,
        training=profile.training,
        base_url=_base_url(profile.config_json, profile.kind),
        details=_option_details(profile),
        tags=profile.tags,
    )


async def _get_connector_and_kind(session: AsyncSession, profile_ref: str) -> tuple[ConnectorInstance, ConnectionProfileKind]:
    kind, connector_id = _parse_profile_ref(profile_ref)
    connector = await connector_repository.get_instance(session, connector_id)
    if connector is None:
        raise NotFoundError("Connection profile not found")
    kinds = connector_profile_kinds(connector)
    if kind is None:
        if not kinds:
            raise NotFoundError("Connection profile not found")
        kind = kinds[0]
    if kind not in kinds:
        raise NotFoundError("Connection profile not found")
    return connector, kind  # type: ignore[return-value]


def _parse_profile_ref(profile_ref: str) -> tuple[str | None, UUID]:
    try:
        if ":" in profile_ref:
            kind, connector_id = profile_ref.split(":", 1)
            if kind not in PROFILE_KINDS:
                raise NotFoundError("Connection profile not found")
            return kind, UUID(connector_id)
        return None, UUID(profile_ref)
    except ValueError as exc:
        raise NotFoundError("Connection profile not found") from exc


def _connector_payload_from_profile(payload: ConnectionProfileCreate) -> tuple[str, ConnectorDirection, dict[str, Any]]:
    config = dict(payload.config_json or {})
    if payload.kind == "onec_odata":
        return "onec", ConnectorDirection.BIDIRECTIONAL, _onec_odata_config(config, payload)
    if payload.kind == "onec_http_service":
        return "onec", ConnectorDirection.BIDIRECTIONAL, _onec_http_config(config, payload)
    if payload.kind == "rest_api":
        return "rest", ConnectorDirection.TARGET, _rest_config(config, payload)
    if payload.kind == "printer":
        if config.get("url") and not config.get("host"):
            return "rest", ConnectorDirection.TARGET, _rest_config({**config, "training_mock_printer": bool(config.get("training_mock_printer"))}, payload)
        return "zpl_printer", ConnectorDirection.TARGET, _printer_config(config, payload)
    if payload.kind == "smb_share":
        return "smb_share", ConnectorDirection.TARGET, _metadata_config(config, payload)
    if payload.kind == "local_directory":
        return "local_directory", ConnectorDirection.TARGET, _metadata_config(config, payload)
    if payload.kind == "training_mock":
        training_config = {"url": "/api/training/mock-dnp/marking/pools", "method": "POST", "training_mock_generic": True, **config}
        return "rest", ConnectorDirection.TARGET, _metadata_config(training_config, payload)
    raise BadRequestError("Unsupported connection profile kind")


def _onec_odata_config(config: dict[str, Any], payload: ConnectionProfileCreate) -> dict[str, Any]:
    base_url = str(config.get("base_url") or config.get("url") or "").strip()
    if not base_url:
        raise BadRequestError("base_url is required for 1C OData profiles")
    return _metadata_config(
        {
            **config,
            "base_url": base_url,
            "auth": _auth_config(config),
            "timeout_seconds": int(config.get("timeout_seconds") or 20),
            "verify_ssl": config.get("verify_ssl", True) is not False,
            "odata": {
                **(config.get("odata") if isinstance(config.get("odata"), dict) else {}),
                "enabled": True,
                "default_page_size": int(config.get("default_top") or config.get("default_page_size") or 100),
                "max_pages": int(config.get("max_pages") or 10),
            },
        },
        payload,
    )


def _onec_http_config(config: dict[str, Any], payload: ConnectionProfileCreate) -> dict[str, Any]:
    base_url = str(config.get("http_service_base_url") or config.get("base_url") or config.get("url") or "").strip()
    if not base_url:
        raise BadRequestError("http_service_base_url or base_url is required for 1C HTTP Service profiles")
    http_services = config.get("http_services") if isinstance(config.get("http_services"), dict) else {}
    health_path = config.get("health_path") or http_services.get("health_path")
    return _metadata_config(
        {
            **config,
            "http_service_base_url": base_url,
            "auth": _auth_config(config),
            "timeout_seconds": int(config.get("timeout_seconds") or 20),
            "verify_ssl": config.get("verify_ssl", True) is not False,
            "http_services": {
                **(config.get("http_services") if isinstance(config.get("http_services"), dict) else {}),
                "enabled": True,
                "health_path": health_path,
            },
        },
        payload,
    )


def _rest_config(config: dict[str, Any], payload: ConnectionProfileCreate) -> dict[str, Any]:
    url = str(config.get("url") or config.get("base_url") or "").strip()
    if not url:
        raise BadRequestError("url or base_url is required for REST API profiles")
    return _metadata_config({**config, "url": url, "method": str(config.get("method") or "POST").upper()}, payload)


def _printer_config(config: dict[str, Any], payload: ConnectionProfileCreate) -> dict[str, Any]:
    host = str(config.get("host") or "").strip()
    if not host:
        raise BadRequestError("host is required for printer profiles")
    return _metadata_config({**config, "host": host, "port": int(config.get("port") or 9100), "dpi": int(config.get("dpi") or 203)}, payload)


def _auth_config(config: dict[str, Any]) -> dict[str, Any]:
    existing = config.get("auth") if isinstance(config.get("auth"), dict) else {}
    auth_type = str(config.get("auth_type") or existing.get("type") or "none")
    auth: dict[str, Any] = {"type": auth_type}
    if auth_type == "basic":
        auth["username"] = str(config.get("username") or existing.get("username") or "")
        password = config.get("password", existing.get("password"))
        password_secret = config.get("password_secret") or existing.get("password_secret")
        if isinstance(password, str) and password.startswith("$secret:"):
            password = {"$secret": password.replace("$secret:", "", 1)}
        elif password_secret:
            password = {"$secret": str(password_secret)}
        auth["password"] = password or ""
    return auth


def _metadata_config(config: dict[str, Any], payload: ConnectionProfileCreate) -> dict[str, Any]:
    omh = config.get("omh") if isinstance(config.get("omh"), dict) else {}
    return {
        **config,
        "omh": {
            **omh,
            "profile": "connection_center",
            "connection_profile_kind": payload.kind,
            "description": payload.description,
            "tags": payload.tags,
            "package_id": payload.package_id,
        },
    }


def _merge_config(current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(current)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_config(merged[key], value)
        else:
            merged[key] = value
    return merged


def _base_url(config: dict[str, Any], kind: ConnectionProfileKind) -> str | None:
    if kind == "onec_odata":
        return _string(config.get("base_url"))
    if kind == "onec_http_service":
        return _string(config.get("http_service_base_url") or config.get("url") or config.get("base_url"))
    if kind in {"rest_api", "training_mock"}:
        return _string(config.get("url") or config.get("base_url"))
    if kind == "printer":
        if config.get("host"):
            return f"tcp://{config.get('host')}:{config.get('port') or 9100}"
        return _string(config.get("url"))
    if kind == "smb_share":
        return _string(config.get("unc_path") or config.get("path"))
    if kind == "local_directory":
        return _string(config.get("path") or config.get("directory"))
    return None


def _option_details(profile: ConnectionProfileRead) -> dict[str, Any]:
    config = profile.config_json
    if profile.kind == "printer":
        return {"host": config.get("host"), "port": config.get("port"), "printer_name": config.get("printer_name") or profile.name}
    if profile.kind == "smb_share":
        return {"unc_path": config.get("unc_path") or config.get("path")}
    if profile.kind == "local_directory":
        return {"path": config.get("path") or config.get("directory")}
    return {"base_url": _base_url(config, profile.kind)}


def _string(value: Any) -> str | None:
    return str(value) if isinstance(value, str) and value else None


def _package_id(kind: str) -> str | None:
    if kind in {"onec_odata", "onec_http_service"}:
        return "omh-package-onec"
    if kind == "printer":
        return "omh-package-printer"
    return None


def _used_by(kind: str) -> list[str]:
    return {
        "onec_odata": ["Request -> OData -> Response", "Request -> OData -> Send Endpoint", "DnP CHZ wizard", "Poll OData -> Send Target"],
        "onec_http_service": ["WMS -> 1C HTTP Service", "Source Web API -> Writeback 1C", "XML Raw Bridge"],
        "rest_api": ["Send Endpoint", "DnP API", "External API writeback", "Poll OData -> Send Target"],
        "printer": ["Request -> Printer", "Printing package"],
        "smb_share": ["CHZ Code Pool Workbench", "File targets"],
        "local_directory": ["CHZ Code Pool Workbench", "File targets"],
        "training_mock": ["Training Sandbox", "Executable docs"],
    }.get(kind, [])
