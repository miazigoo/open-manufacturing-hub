from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from app.connectors.builtin.onec import errors
from app.connectors.builtin.onec.client import OneCHTTPClient, join_url
from app.connectors.builtin.onec.http_service import call_http_service, request_body, resolve_operation, standard_envelope
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
        for operation, operation_config in (config.get("operations") or {}).items():
            if not isinstance(operation_config, dict):
                errors_list.append(f"operations.{operation} must be an object")
                continue
            operation_type = operation_config.get("type")
            if operation_type not in {None, "http_service", "odata_lookup", "printing"}:
                errors_list.append(f"operations.{operation}.type must be http_service, odata_lookup or printing")
            method = str(operation_config.get("method", "POST")).upper()
            if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                errors_list.append(f"operations.{operation}.method is not supported")
            path = operation_config.get("path")
            if path is not None and not str(path).startswith("/"):
                errors_list.append(f"operations.{operation}.path must start with /")
            body_mode = operation_config.get("body_mode", "json_envelope")
            if body_mode not in {"json_envelope", "raw_xml", "plain_text"}:
                errors_list.append(f"operations.{operation}.body_mode must be json_envelope, raw_xml or plain_text")
            content_type = operation_config.get("content_type", "application/json")
            if not isinstance(content_type, str) or "/" not in content_type:
                errors_list.append(f"operations.{operation}.content_type must be a valid media type")
        return ConnectorConfigValidationResult(valid=not errors_list, errors=errors_list, warnings=["Use Secrets Store references for 1C passwords in production configs."] if auth_type == "basic" else [])

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
        return _send_result(success, status_code, request_payload, response_payload, error_code, error_message)

    async def dry_run_send(self, config: dict[str, Any], payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        operation, method, path, options, error = resolve_operation(config, payload)
        url = join_url(str(config.get("http_service_base_url") or "http://1c-service"), path)
        body, raw_content = request_body(payload, context, options)
        request_payload = {"method": method, "url": url, "body": body, "operation": operation}
        if raw_content is not None:
            request_payload["body"] = {"text_preview": raw_content[:2000], "size_bytes": len(raw_content.encode("utf-8"))}
            request_payload["headers"] = {"Content-Type": str(options["content_type"])}
            request_payload["body_mode"] = options["body_mode"]
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


def _send_result(
    success: bool,
    status_code: int | None,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any] | None,
    error_code: str | None,
    error_message: str | None,
) -> ConnectorSendResult:
    body = response_payload.get("body") if isinstance(response_payload, dict) else None
    headers = response_payload.get("headers") if isinstance(response_payload, dict) else None
    content_type = response_payload.get("content_type") if isinstance(response_payload, dict) else None
    raw_text = body.get("text") if isinstance(body, dict) and isinstance(body.get("text"), str) else None
    raw_json = body if isinstance(body, (dict, list)) and raw_text is None else None
    external_code = body.get("error_code") if isinstance(body, dict) and body.get("error_code") else None
    external_message = body.get("error_message") if isinstance(body, dict) and body.get("error_message") else None
    if raw_text is None and isinstance(body, str):
        raw_text = body
    human_title = None
    human_summary = None
    developer_message = None
    hint = None
    if not success:
        human_title = "1C rejected operation" if status_code is None or status_code < 500 else "1C HTTP service error"
        human_summary = f"1C says: {external_message or error_message or 'operation failed'}"
        if status_code:
            human_summary = f"1C HTTP {status_code}: {external_message or error_message or 'operation failed'}"
        developer_message = "Original 1C response is preserved in incoming_response.json and external_error.json artifacts."
        hint = "Check the 1C document, HTTP service handler, operation path and mapping, then replay from the failed step."
    return ConnectorSendResult(
        success=success,
        status_code=status_code,
        request_payload=request_payload,
        response_payload=response_payload,
        error_code=error_code,
        error_message=error_message,
        external_error_code=str(external_code or error_code) if error_code else None,
        external_error_message=str(external_message or error_message) if error_message else None,
        external_error_type="business_error" if status_code and status_code < 400 else "http_error" if status_code else "connection_error",
        developer_message=developer_message,
        human_title=human_title,
        human_summary=human_summary,
        hint=hint,
        raw_response_text=raw_text,
        raw_response_json=raw_json,
        response_headers=headers,
        response_content_type=content_type,
        endpoint_url=request_payload.get("url"),
        operation=request_payload.get("operation"),
    )
