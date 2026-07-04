from urllib.parse import urlparse

import httpx

from app.core.enums import ConnectorDirection, HealthStatus
from app.sdk.types import ConnectorConfigValidationResult, ConnectorContext, ConnectorHealthResult, ConnectorReceivedEvent, ConnectorSendResult


class RESTConnector:
    connector_type = "rest"
    display_name = "REST Connector"
    direction = ConnectorDirection.TARGET

    async def validate_config(self, config: dict) -> ConnectorConfigValidationResult:
        errors: list[str] = []
        url = config.get("url")
        parsed = urlparse(url or "")
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            errors.append("url must be a valid http or https URL")
        method = str(config.get("method", "POST")).upper()
        if method not in {"POST", "PUT", "PATCH"}:
            errors.append("method must be POST, PUT or PATCH")
        return ConnectorConfigValidationResult(valid=not errors, errors=errors)

    async def healthcheck(self, config: dict) -> ConnectorHealthResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorHealthResult(status=HealthStatus.WARNING, message="Invalid REST connector config", details={"errors": validation.errors})
        return ConnectorHealthResult(status=HealthStatus.UNKNOWN, message="REST target configured; active send not tested", details={"url": config.get("url")})

    async def send(self, config: dict, payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorSendResult(success=False, error_code="INVALID_CONNECTOR_CONFIG", error_message="; ".join(validation.errors))
        method = str(config.get("method", "POST")).upper()
        url = str(config["url"])
        headers = config.get("headers") or {}
        timeout = float(config.get("timeout_seconds", 10))
        request_payload = {"method": method, "url": url, "headers": headers, "body": payload}
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, json=payload, headers=headers)
            try:
                response_body = response.json()
                raw_json = response_body
                raw_text = None
            except Exception:
                response_body = {"text": response.text}
                raw_json = None
                raw_text = response.text
            content_type = response.headers.get("content-type")
            success = 200 <= response.status_code < 300
            message = _external_message(response_body)
            return ConnectorSendResult(
                success=success,
                status_code=response.status_code,
                request_payload=request_payload,
                response_payload={"status_code": response.status_code, "headers": dict(response.headers), "content_type": content_type, "body": response_body},
                error_code=None if success else "REST_NON_2XX",
                error_message=None if success else message or f"REST target returned {response.status_code}",
                external_error_message=None if success else message,
                external_error_type=None if success else "http_error",
                human_title=None if success else "External API returned an error",
                human_summary=None if success else f"External API HTTP {response.status_code}: {message or 'request failed'}",
                developer_message=None if success else "Original REST response is preserved in incoming_response.json and external_error.json artifacts.",
                hint=None if success else "Check API credentials, endpoint contract and request payload before replay.",
                raw_response_json=raw_json if isinstance(raw_json, (dict, list)) else None,
                raw_response_text=raw_text,
                response_headers=dict(response.headers),
                response_content_type=content_type,
                endpoint_url=url,
                operation=method,
            )
        except Exception as exc:
            return ConnectorSendResult(
                success=False,
                request_payload=request_payload,
                error_code="REST_SEND_FAILED",
                error_message=str(exc),
                external_error_message=str(exc),
                external_error_type="connection_error",
                human_title="External API is unreachable",
                human_summary=f"REST send failed: {exc}",
                developer_message=str(exc),
                hint="Check network connectivity, DNS, TLS and target API availability.",
                endpoint_url=url,
                operation=method,
            )

    async def dry_run_send(self, config: dict, payload: dict, context: ConnectorContext) -> ConnectorSendResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorSendResult(success=False, error_code="INVALID_CONNECTOR_CONFIG", error_message="; ".join(validation.errors))
        return ConnectorSendResult(
            success=True,
            status_code=200,
            request_payload={"method": str(config.get("method", "POST")).upper(), "url": config.get("url"), "headers": config.get("headers") or {}, "body": payload},
            response_payload={"dry_run": True},
        )

    async def receive(self, config: dict, context: ConnectorContext) -> list[ConnectorReceivedEvent]:
        return []


def _external_message(body: object) -> str | None:
    if isinstance(body, dict):
        for key in ("error_message", "message", "detail", "description", "error"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in body.values():
            nested = _external_message(value)
            if nested:
                return nested
    if isinstance(body, list):
        for item in body:
            nested = _external_message(item)
            if nested:
                return nested
    return None
