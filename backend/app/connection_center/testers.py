from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.builtin.onec.client import OneCHTTPClient, join_url
from app.connectors.builtin.onec.odata import read_odata
from app.connectors.models import ConnectorInstance
from app.connectors.registry import registry
from app.connection_center.schemas import ConnectionProfileKind, ConnectionProfileTestRequest, ConnectionProfileTestResponse
from app.core.enums import ConnectorInstanceStatus, HealthStatus
from app.odata_connections.schemas import ODataConnectionTestRequest
from app.odata_connections.service import test_connection as test_odata_connection
from app.packages_training.mock_odata import metadata_xml, query_mock_odata
from app.sdk.types import ConnectorContext
from app.secrets.service import SecretResolver


async def test_profile(session: AsyncSession, connector: ConnectorInstance, kind: ConnectionProfileKind, profile_id: str, request: ConnectionProfileTestRequest) -> ConnectionProfileTestResponse:
    if kind == "onec_odata":
        return await _test_odata(session, connector, profile_id, request)
    if kind == "onec_http_service":
        return await _test_onec_http(session, connector, profile_id, request)
    if kind in {"rest_api", "training_mock"}:
        return await _test_rest(session, connector, kind, profile_id, request)
    if kind == "printer":
        return await _test_printer(session, connector, profile_id, request)
    if kind == "smb_share":
        return await _test_smb(session, connector, profile_id, request)
    if kind == "local_directory":
        return await _test_local_directory(session, connector, profile_id, request)
    return _response(False, "failed", "Unsupported connection profile kind", profile_id, connector.id, kind, request.dry_run)


async def _test_odata(session: AsyncSession, connector: ConnectorInstance, profile_id: str, request: ConnectionProfileTestRequest) -> ConnectionProfileTestResponse:
    payload = ODataConnectionTestRequest(resource=request.resource or "$metadata", top=request.top, filter=request.filter)
    result = await test_odata_connection(session, connector.id, payload)
    return ConnectionProfileTestResponse(
        success=bool(result.get("success")),
        status=str(result.get("status") or ("ok" if result.get("success") else "failed")),
        message=_friendly_odata_message(result),
        profile_id=profile_id,
        connector_id=connector.id,
        kind="onec_odata",
        dry_run=True,
        request=result.get("request") or {},
        response=result.get("response") or {},
        sample_items=result.get("sample_items") or [],
    )


async def _test_onec_http(session: AsyncSession, connector: ConnectorInstance, profile_id: str, request: ConnectionProfileTestRequest) -> ConnectionProfileTestResponse:
    config = await SecretResolver(session).resolve_config(connector.config_json or {})
    base_url = str(config.get("http_service_base_url") or config.get("url") or config.get("base_url") or "")
    http_services = config.get("http_services") if isinstance(config.get("http_services"), dict) else {}
    health_path = request.health_path or http_services.get("health_path")
    if not health_path:
        return _response(True, "configured", "1C HTTP Service profile is configured. No health endpoint is set, so no external request was sent.", profile_id, connector.id, "onec_http_service", True, request={"base_url": base_url})
    if request.dry_run:
        return _response(True, "dry_run", "1C HTTP health request is prepared but not sent.", profile_id, connector.id, "onec_http_service", True, request={"method": "GET", "url": _join(base_url, str(health_path))})
    client = OneCHTTPClient(config if connector.connector_type == "onec" else {"timeout_seconds": config.get("timeout_seconds", 10), "verify_ssl": config.get("verify_ssl", True), "auth": config.get("auth") or {"type": "none"}})
    response, request_payload, error_code, error_message = await client.request("GET", _join(base_url, str(health_path)))
    if error_code or response is None:
        return _response(False, "failed", _friendly_http_error(error_message or error_code or "1C HTTP Service request failed"), profile_id, connector.id, "onec_http_service", False, request=request_payload or {})
    return _response(response.status_code < 400, "ok" if response.status_code < 400 else "failed", f"1C HTTP Service returned HTTP {response.status_code}", profile_id, connector.id, "onec_http_service", False, request=request_payload or {}, response={"status_code": response.status_code, "body_preview": response.text[:1000]})


async def _test_rest(session: AsyncSession, connector: ConnectorInstance, kind: ConnectionProfileKind, profile_id: str, request: ConnectionProfileTestRequest) -> ConnectionProfileTestResponse:
    config = await SecretResolver(session).resolve_config(connector.config_json or {})
    url = str(config.get("url") or config.get("base_url") or "")
    method = str(config.get("method") or "GET").upper()
    if request.custom_path:
        url = _join(url, request.custom_path)
    parsed = urlparse(url)
    if not (url.startswith("/") or (parsed.scheme in {"http", "https"} and parsed.netloc)):
        return _response(False, "failed", "REST URL is invalid. Use http(s) URL or a Training mock path.", profile_id, connector.id, kind, True, request={"url": url})
    return _response(True, "dry_run" if request.dry_run else "configured", "REST API profile is configured. Dry-run does not send an external request.", profile_id, connector.id, kind, True, request={"method": method, "url": url, "headers": config.get("headers") or {}})


async def _test_printer(session: AsyncSession, connector: ConnectorInstance, profile_id: str, request: ConnectionProfileTestRequest) -> ConnectionProfileTestResponse:
    config = await SecretResolver(session).resolve_config(connector.config_json or {})
    if connector.connector_type == "zpl_printer" and request.confirm_print:
        connector_impl = registry.get("zpl_printer")
        result = await connector_impl.dry_run_send(config, _printer_payload(request), ConnectorContext(dry_run=True, correlation_id="connection-center-test"))
        return _connector_send_response(result.success, "ok" if result.success else "failed", result.error_message or "Printer dry-run succeeded", profile_id, connector.id, "printer", True, result.request_payload, result.response_payload)
    if connector.connector_type == "zpl_printer":
        connector_impl = registry.get("zpl_printer")
        result = await connector_impl.dry_run_send(config, _printer_payload(request), ConnectorContext(dry_run=True, correlation_id="connection-center-test"))
        warnings = [] if request.confirm_print else ["Real print is not executed from Connection Center unless confirm_print=true."]
        return _connector_send_response(result.success, "dry_run" if result.success else "failed", result.error_message or "Printer dry-run prepared. No label was sent.", profile_id, connector.id, "printer", True, result.request_payload, result.response_payload, warnings)
    url = str(config.get("url") or "")
    return _response(True, "dry_run", "Training printer/mock is configured. No real label was sent.", profile_id, connector.id, "printer", True, request={"url": url}, response={"dry_run": True})


async def _test_smb(session: AsyncSession, connector: ConnectorInstance, profile_id: str, request: ConnectionProfileTestRequest) -> ConnectionProfileTestResponse:
    config = await SecretResolver(session).resolve_config(connector.config_json or {})
    unc_path = str(config.get("unc_path") or config.get("path") or "")
    if not (unc_path.startswith("\\\\") or unc_path.startswith("smb://")):
        return _response(False, "failed", "SMB path must look like \\\\server\\share or smb://server/share.", profile_id, connector.id, "smb_share", True, request={"unc_path": unc_path})
    warnings = [] if request.confirm_write else ["Write/delete probe was not executed. Pass confirm_write=true only for a safe test share."]
    return _response(True, "dry_run", "SMB share path is configured. Network write probe is dry-run only in this environment.", profile_id, connector.id, "smb_share", True, request={"unc_path": unc_path}, response={"dry_run": True}, warnings=warnings)


async def _test_local_directory(session: AsyncSession, connector: ConnectorInstance, profile_id: str, request: ConnectionProfileTestRequest) -> ConnectionProfileTestResponse:
    config = await SecretResolver(session).resolve_config(connector.config_json or {})
    directory = Path(str(config.get("path") or config.get("directory") or "")).expanduser()
    if not directory.exists():
        if config.get("create_if_missing") and request.confirm_write:
            directory.mkdir(parents=True, exist_ok=True)
        else:
            return _response(False, "failed", "Local directory does not exist. Enable create_if_missing and confirm_write only for a safe path.", profile_id, connector.id, "local_directory", request.dry_run, request={"path": str(directory)})
    if not directory.is_dir():
        return _response(False, "failed", "Local directory path points to a file, not a directory.", profile_id, connector.id, "local_directory", request.dry_run, request={"path": str(directory)})
    if request.confirm_write:
        probe = directory / ".omh-connection-center-test"
        try:
            probe.write_text("connection-center-test", encoding="utf-8")
            probe.unlink(missing_ok=True)
        except OSError as exc:
            return _response(False, "failed", f"Local directory write/delete probe failed: {exc}", profile_id, connector.id, "local_directory", False, request={"path": str(directory)})
        return _response(True, "ok", "Local directory is writable. Test file was created and deleted.", profile_id, connector.id, "local_directory", False, request={"path": str(directory)}, response={"write_delete_probe": "ok"})
    writable = directory.is_dir()
    return _response(writable, "dry_run" if writable else "failed", "Local directory exists. Write/delete probe was not executed without confirm_write=true.", profile_id, connector.id, "local_directory", True, request={"path": str(directory)}, response={"exists": True}, warnings=["Write/delete probe was skipped."])


def update_connector_health(connector: ConnectorInstance, result: ConnectionProfileTestResponse) -> None:
    connector.last_health_status = HealthStatus.OK if result.success else HealthStatus.DOWN
    connector.last_health_message = result.message
    if connector.enabled:
        connector.status = ConnectorInstanceStatus.ENABLED


def _friendly_odata_message(result: dict[str, Any]) -> str:
    message = str(result.get("message") or "")
    if "401" in message:
        return "OData authentication failed: check username/password or secret reference."
    if "metadata" in message.lower() and not result.get("success"):
        return f"OData metadata check failed: {message}"
    return message or ("OData check succeeded" if result.get("success") else "OData check failed")


def _friendly_http_error(message: str) -> str:
    lowered = message.lower()
    if "timeout" in lowered:
        return "REST/1C HTTP timeout: check host, firewall and timeout_seconds."
    if "401" in lowered or "unauthorized" in lowered:
        return "Authentication failed: check credentials or secret reference."
    return message


def _printer_payload(request: ConnectionProfileTestRequest) -> dict[str, Any]:
    zpl = request.payload.get("zpl") if isinstance(request.payload, dict) else None
    return {
        "job_id": request.payload.get("job_id", "connection-center-test") if isinstance(request.payload, dict) else "connection-center-test",
        "line_id": request.payload.get("line_id", "test-line") if isinstance(request.payload, dict) else "test-line",
        "zpl": zpl if isinstance(zpl, str) and zpl.strip() else "^XA\n^FO30,30^A0N,30,30^FDCONNECTION TEST^FS\n^XZ",
    }


def _join(base_url: str, path: str) -> str:
    if not path:
        return base_url
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if base_url.startswith("/"):
        return f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    return urljoin(f"{base_url.rstrip('/')}/", path.lstrip("/"))


def _connector_send_response(success: bool, status: str, message: str, profile_id: str, connector_id: UUID, kind: ConnectionProfileKind, dry_run: bool, request_payload: dict[str, Any] | None, response_payload: dict[str, Any] | None, warnings: list[str] | None = None) -> ConnectionProfileTestResponse:
    return ConnectionProfileTestResponse(success=success, status=status, message=message, profile_id=profile_id, connector_id=connector_id, kind=kind, dry_run=dry_run, request=request_payload or {}, response=response_payload or {}, warnings=warnings or [])


def _response(success: bool, status: str, message: str, profile_id: str, connector_id: UUID, kind: ConnectionProfileKind, dry_run: bool, *, request: dict[str, Any] | None = None, response: dict[str, Any] | None = None, warnings: list[str] | None = None) -> ConnectionProfileTestResponse:
    return ConnectionProfileTestResponse(success=success, status=status, message=message, profile_id=profile_id, connector_id=connector_id, kind=kind, dry_run=dry_run, request=request or {}, response=response or {}, warnings=warnings or [])
