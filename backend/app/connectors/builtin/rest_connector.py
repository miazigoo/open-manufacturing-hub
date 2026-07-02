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
            except Exception:
                response_body = {"text": response.text}
            return ConnectorSendResult(
                success=200 <= response.status_code < 300,
                status_code=response.status_code,
                request_payload=request_payload,
                response_payload=response_body if isinstance(response_body, dict) else {"body": response_body},
                error_code=None if response.status_code < 400 else "REST_NON_2XX",
                error_message=None if response.status_code < 400 else f"REST target returned {response.status_code}",
            )
        except Exception as exc:
            return ConnectorSendResult(success=False, request_payload=request_payload, error_code="REST_SEND_FAILED", error_message=str(exc))

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
