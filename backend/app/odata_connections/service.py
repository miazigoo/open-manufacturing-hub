from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import service as connector_service
from app.connectors.builtin.onec.client import OneCHTTPClient, join_url
from app.connectors.builtin.onec.odata import read_odata
from app.connectors.models import ConnectorInstance
from app.connectors.schemas import ConnectorInstanceCreate, ConnectorInstancePatch
from app.core.enums import ConnectorDirection
from app.core.errors import BadRequestError, NotFoundError
from app.odata_connections.schemas import ODataConnectionCreate, ODataConnectionPatch, ODataConnectionRead, ODataConnectionTestRequest
from app.packages_training.mock_odata import metadata_xml, query_mock_odata
from app.secrets.service import SecretResolver


def _is_odata_connection(connector: ConnectorInstance) -> bool:
    if connector.connector_type != "onec":
        return False
    config = connector.config_json or {}
    odata = config.get("odata") if isinstance(config.get("odata"), dict) else {}
    return bool(config.get("base_url")) and odata.get("enabled", True) is not False


def _password_reference(secret_name: str | None) -> dict[str, str] | None:
    return {"$secret": secret_name} if secret_name else None


def _config_from_payload(payload: ODataConnectionCreate | ODataConnectionPatch, previous: dict[str, Any] | None = None) -> dict[str, Any]:
    previous = previous or {}
    auth_previous = previous.get("auth") if isinstance(previous.get("auth"), dict) else {}
    odata_previous = previous.get("odata") if isinstance(previous.get("odata"), dict) else {}
    metadata_previous = previous.get("omh") if isinstance(previous.get("omh"), dict) else {}
    data = payload.model_dump(exclude_unset=True)
    auth_type = data.get("auth_type", auth_previous.get("type", "none"))
    auth: dict[str, Any] = {"type": auth_type}
    username = data.get("username", auth_previous.get("username"))
    password = data.get("password")
    password_secret = data.get("password_secret")
    previous_password = auth_previous.get("password")
    if auth_type == "basic":
        auth["username"] = username or ""
        auth["password"] = password if password is not None else _password_reference(password_secret) or previous_password or ""
    config = {
        **previous,
        "base_url": data.get("base_url", previous.get("base_url", "")),
        "auth": auth,
        "timeout_seconds": data.get("timeout_seconds", previous.get("timeout_seconds", 20)),
        "verify_ssl": data.get("verify_ssl", previous.get("verify_ssl", True)),
        "odata": {
            **odata_previous,
            "enabled": True,
            "default_page_size": data.get("default_top", odata_previous.get("default_page_size", 100)),
            "max_pages": data.get("max_pages", odata_previous.get("max_pages", 10)),
        },
        "omh": {
            **metadata_previous,
            "profile": "odata_connection",
            "description": data.get("description", metadata_previous.get("description")),
            "tags": data.get("tags", metadata_previous.get("tags", [])),
        },
    }
    return config


def _read(connector: ConnectorInstance) -> ODataConnectionRead:
    config = connector.config_json or {}
    auth = config.get("auth") if isinstance(config.get("auth"), dict) else {}
    odata = config.get("odata") if isinstance(config.get("odata"), dict) else {}
    omh = config.get("omh") if isinstance(config.get("omh"), dict) else {}
    password = auth.get("password")
    password_secret = password.get("$secret") if isinstance(password, dict) else None
    return ODataConnectionRead(
        id=connector.id,
        connector_id=connector.id,
        name=connector.name,
        description=omh.get("description"),
        base_url=str(config.get("base_url") or ""),
        auth_type=str(auth.get("type") or "none"),
        username=auth.get("username") if isinstance(auth.get("username"), str) else None,
        password_secret=password_secret,
        timeout_seconds=int(config.get("timeout_seconds") or 20),
        verify_ssl=config.get("verify_ssl") is not False,
        default_top=int(odata.get("default_page_size") or 100),
        max_pages=int(odata.get("max_pages") or 10),
        tags=omh.get("tags") if isinstance(omh.get("tags"), list) else [],
        enabled=connector.enabled,
        status=connector.status.value if hasattr(connector.status, "value") else str(connector.status),
        last_health_status=connector.last_health_status,
        last_health_message=connector.last_health_message,
        last_health_at=connector.last_health_at,
        config_json=config,
        created_at=connector.created_at,
        updated_at=connector.updated_at,
    )


async def list_connections(session: AsyncSession) -> list[ODataConnectionRead]:
    result = await session.execute(select(ConnectorInstance).where(ConnectorInstance.connector_type == "onec").order_by(ConnectorInstance.name.asc()))
    return [_read(connector) for connector in result.scalars().all() if _is_odata_connection(connector)]


async def get_connection(session: AsyncSession, connection_id: UUID) -> ODataConnectionRead:
    connector = await session.get(ConnectorInstance, connection_id)
    if connector is None or not _is_odata_connection(connector):
        raise NotFoundError("OData connection not found")
    return _read(connector)


async def create_connection(session: AsyncSession, payload: ODataConnectionCreate) -> ODataConnectionRead:
    if payload.auth_type not in {"none", "basic"}:
        raise BadRequestError("auth_type must be none or basic")
    config = _config_from_payload(payload)
    if payload.connector_id:
        connector = await session.get(ConnectorInstance, payload.connector_id)
        if connector is None or connector.connector_type != "onec":
            raise NotFoundError("1C connector not found")
        connector.name = payload.name
        connector.direction = ConnectorDirection.BIDIRECTIONAL
        connector.config_json = config
        connector.enabled = True
        await session.flush()
        return _read(connector)
    connector = await connector_service.create_instance(session, ConnectorInstanceCreate(name=payload.name, connector_type="onec", direction=ConnectorDirection.BIDIRECTIONAL, enabled=True, config_json=config))
    return _read(connector)


async def patch_connection(session: AsyncSession, connection_id: UUID, payload: ODataConnectionPatch) -> ODataConnectionRead:
    connector = await session.get(ConnectorInstance, connection_id)
    if connector is None or connector.connector_type != "onec":
        raise NotFoundError("OData connection not found")
    config = _config_from_payload(payload, connector.config_json or {})
    patch_data: dict[str, Any] = {"config_json": config}
    if payload.name is not None:
        patch_data["name"] = payload.name
    if payload.enabled is not None:
        patch_data["enabled"] = payload.enabled
    patch = ConnectorInstancePatch(**patch_data)
    await connector_service.patch_instance(session, connector.id, patch)
    return _read(connector)


async def delete_connection(session: AsyncSession, connection_id: UUID) -> None:
    connector = await session.get(ConnectorInstance, connection_id)
    if connector is None or connector.connector_type != "onec":
        raise NotFoundError("OData connection not found")
    await session.delete(connector)


async def options(session: AsyncSession) -> list[dict[str, Any]]:
    return [{"id": item.id, "connector_id": item.connector_id, "label": item.name, "base_url": item.base_url, "enabled": item.enabled, "tags": item.tags} for item in await list_connections(session)]


async def test_connection(session: AsyncSession, connection_id: UUID, request: ODataConnectionTestRequest) -> dict[str, Any]:
    connector = await session.get(ConnectorInstance, connection_id)
    if connector is None or not _is_odata_connection(connector):
        raise NotFoundError("OData connection not found")
    config = await SecretResolver(session).resolve_config(connector.config_json)
    mock_odata = config.get("mock_odata") if isinstance(config.get("mock_odata"), dict) else None
    if mock_odata:
        if request.resource == "$metadata":
            return {"success": True, "status": "ok", "message": "Training mock OData metadata is available", "connector_id": connector.id, "request": {"mock": True, "resource": "$metadata"}, "response": {"status_code": 200, "body_preview": metadata_xml(mock_odata)[:1000]}, "sample_items": []}
        params: dict[str, Any] = {"$top": request.top or 5}
        if request.filter:
            params["$filter"] = request.filter
        response = query_mock_odata(mock_odata, request.resource, params)
        items = response.get("value") if isinstance(response.get("value"), list) else []
        return {"success": True, "status": "ok", "message": "Training mock OData query succeeded", "connector_id": connector.id, "request": {"mock": True, "resource": request.resource, "params": params}, "response": response, "sample_items": items[:5]}
    if request.resource == "$metadata":
        client = OneCHTTPClient(config)
        response, request_payload, error_code, error_message = await client.request("GET", join_url(str(config.get("base_url") or ""), "$metadata"))
        if error_code or response is None:
            return {"success": False, "status": "failed", "message": error_message or error_code or "OData metadata request failed", "connector_id": connector.id, "request": request_payload, "response": {}, "sample_items": []}
        return {"success": response.status_code < 400, "status": "ok" if response.status_code < 400 else "failed", "message": f"1C metadata returned HTTP {response.status_code}", "connector_id": connector.id, "request": request_payload, "response": {"status_code": response.status_code, "body_preview": response.text[:1000]}, "sample_items": []}
    params: dict[str, Any] = {"$top": request.top or 5}
    if request.filter:
        params["$filter"] = request.filter
    result = await read_odata(config, request.resource, params)
    return {"success": result.success, "status": "ok" if result.success else "failed", "message": "OData query succeeded" if result.success else result.error_message or result.error_code or "OData query failed", "connector_id": connector.id, "request": result.request_payload or {}, "response": result.response_payload or {}, "sample_items": result.items[:5]}
