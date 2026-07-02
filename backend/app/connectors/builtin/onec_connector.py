from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.connectors.builtin.onec import errors
from app.connectors.builtin.onec.client import OneCHTTPClient, join_url
from app.connectors.builtin.onec.http_service import call_http_service, resolve_operation, standard_envelope
from app.connectors.builtin.onec.odata import read_odata as onec_read_odata
from app.connectors.builtin.onec.schemas import OneCReadResult
from app.core.enums import ConnectorDirection, HealthStatus
from app.sdk.types import ConnectorConfigValidationResult, ConnectorContext, ConnectorHealthResult, ConnectorReceivedEvent, ConnectorSendResult


class OneCConnector:
    connector_type = "onec"
    display_name = "1C Connector"
    direction = ConnectorDirection.BIDIRECTIONAL

    async def validate_config(self, config: dict[str, Any]) -> ConnectorConfigValidationResult:
        errors_list: list[str] = []
        base_url = config.get("base_url")
        http_url = config.get("http_service_base_url")
        if not base_url and not http_url:
            errors_list.append("base_url or http_service_base_url is required")
        for field, value in [("base_url", base_url), ("http_service_base_url", http_url)]:
            if value:
                parsed = urlparse(str(value))
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    errors_list.append(f"{field} must be a valid http or https URL")
        timeout = config.get("timeout_seconds", 20)
        if not isinstance(timeout, (int, float)) or float(timeout) <= 0:
            errors_list.append("timeout_seconds must be positive")
        if not isinstance(config.get("verify_ssl", True), bool):
            errors_list.append("verify_ssl must be boolean")
        auth = config.get("auth") or {"type": "none"}
        auth_type = auth.get("type", "none")
        if auth_type not in {"none", "basic"}:
            errors_list.append("auth.type must be none or basic")
        if auth_type == "basic" and (not auth.get("username") or not auth.get("password")):
            errors_list.append("auth.username and auth.password are required for basic auth")
        odata = config.get("odata") or {}
        if odata:
            if not isinstance(odata.get("enabled", True), bool):
                errors_list.append("odata.enabled must be boolean")
            default_page_size = _positive_int(odata.get("default_page_size", 100))
            max_pages = _positive_int(odata.get("max_pages", 10))
            if default_page_size is None:
                errors_list.append("odata.default_page_size must be positive")
            if max_pages is None:
                errors_list.append("odata.max_pages must be positive")
        return ConnectorConfigValidationResult(valid=not errors_list, errors=errors_list, warnings=["TODO: move 1C passwords to encrypted secret storage"] if auth_type == "basic" else [])

    async def healthcheck(self, config: dict[str, Any]) -> ConnectorHealthResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorHealthResult(status=HealthStatus.WARNING, message="Invalid 1C connector config", details={"errors": validation.errors})
        details: dict[str, Any] = {}
        client = OneCHTTPClient(config)
        if (config.get("odata") or {}).get("enabled", True) and config.get("base_url"):
            url = join_url(str(config["base_url"]), "$metadata")
            response, _, error_code, error_message = await client.request("GET", url)
            if error_code:
                return ConnectorHealthResult(status=HealthStatus.DOWN, message=error_message or "1C OData healthcheck failed", details={"error_code": error_code})
            assert response is not None
            details["odata_status_code"] = response.status_code
            if response.status_code == 401:
                return ConnectorHealthResult(status=HealthStatus.DOWN, message="1C returned 401 Unauthorized", details={"status_code": 401, "error_code": errors.ONEC_AUTH_FAILED})
            if response.status_code >= 400:
                return ConnectorHealthResult(status=HealthStatus.DOWN, message=f"1C OData returned {response.status_code}", details=details)
            details["odata"] = "ok"
        if config.get("http_service_base_url") and (config.get("http_services") or {}).get("enabled", True):
            url = join_url(str(config["http_service_base_url"]), _http_health_path(config))
            response, _, error_code, error_message = await client.request("GET", url)
            if error_code:
                return ConnectorHealthResult(status=HealthStatus.DOWN, message=error_message or "1C HTTP service healthcheck failed", details={"error_code": error_code})
            assert response is not None
            details["http_service_status_code"] = response.status_code
            if response.status_code == 401:
                return ConnectorHealthResult(status=HealthStatus.DOWN, message="1C returned 401 Unauthorized", details={"status_code": 401, "error_code": errors.ONEC_AUTH_FAILED})
            if response.status_code >= 400:
                return ConnectorHealthResult(status=HealthStatus.DOWN, message=f"1C HTTP service returned {response.status_code}", details=details)
            details["http_service"] = "ok"
        return ConnectorHealthResult(status=HealthStatus.OK, message="1C service is reachable", details=details)

    async def read_odata(self, config: dict[str, Any], resource: str, query: dict | None = None, context: ConnectorContext | None = None) -> OneCReadResult:
        return await onec_read_odata(config, resource, query)

    async def send(self, config: dict[str, Any], payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorSendResult(False, error_code=errors.ONEC_CONFIG_INVALID, error_message="; ".join(validation.errors))
        success, status_code, request_payload, response_payload, error_code, error_message = await call_http_service(config, payload, context)
        return ConnectorSendResult(success=success, status_code=status_code, request_payload=request_payload, response_payload=response_payload, error_code=error_code, error_message=error_message)

    async def dry_run_send(self, config: dict[str, Any], payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        operation, method, path, error = resolve_operation(config, payload)
        url = join_url(str(config.get("http_service_base_url") or "http://1c-service"), path)
        body = standard_envelope(payload, context)
        request_payload = {"method": method, "url": url, "body": body, "operation": operation}
        if error:
            return ConnectorSendResult(False, request_payload=request_payload, error_code=error["error_code"], error_message=error["error_message"])
        return ConnectorSendResult(success=True, status_code=200, request_payload=request_payload, response_payload={"dry_run": True, "would_call": {"method": method, "url": url}})

    async def receive(self, config: dict, context: ConnectorContext) -> list[ConnectorReceivedEvent]:
        return []


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _http_health_path(config: dict[str, Any]) -> str:
    services = (config.get("http_services") or {}).get("services") or []
    for service in services:
        if service.get("name") == "health" and service.get("path"):
            return str(service["path"])
    return str((config.get("http_services") or {}).get("health_path") or "/health")
