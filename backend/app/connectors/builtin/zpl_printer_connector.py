from __future__ import annotations

import asyncio
import hashlib
import ipaddress
import re
import socket
from typing import Any

from app.core.enums import ConnectorDirection, HealthStatus
from app.sdk.types import ConnectorConfigValidationResult, ConnectorContext, ConnectorHealthResult, ConnectorReceivedEvent, ConnectorSendResult

_HOSTNAME_RE = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))*\.?$")


class ZPLPrinterConnector:
    connector_type = "zpl_printer"
    display_name = "ZPL Printer"
    direction = ConnectorDirection.TARGET

    async def validate_config(self, config: dict[str, Any]) -> ConnectorConfigValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        host = str(config.get("host") or "").strip()
        if not host:
            errors.append("host is required")
        elif not _valid_host(host):
            errors.append("host must be a valid IP address or DNS hostname")

        port = _positive_int(config.get("port", 9100))
        if port is None or port > 65535:
            errors.append("port must be an integer from 1 to 65535")

        dpi = _positive_int(config.get("dpi", 203))
        if dpi is None or dpi > 2400:
            errors.append("dpi must be a positive integer")

        timeout = _positive_float(config.get("timeout_seconds", 5))
        if timeout is None:
            errors.append("timeout_seconds must be a positive number")

        if config.get("status_mode") not in {None, "tcp_connect"}:
            warnings.append("Only status_mode=tcp_connect is currently supported")

        return ConnectorConfigValidationResult(valid=not errors, errors=errors, warnings=warnings)

    async def healthcheck(self, config: dict[str, Any]) -> ConnectorHealthResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorHealthResult(
                status=HealthStatus.WARNING,
                message="Invalid ZPL printer config",
                details={"errors": validation.errors},
            )

        host = str(config["host"]).strip()
        port = int(config.get("port", 9100))
        timeout = float(config.get("timeout_seconds", 5))
        ok, error = await asyncio.to_thread(_tcp_probe, host, port, timeout)
        if not ok:
            return ConnectorHealthResult(
                status=HealthStatus.DOWN,
                message="Printer TCP port is not reachable",
                details={"host": host, "port": port, "error": error},
            )
        return ConnectorHealthResult(status=HealthStatus.OK, message="Printer TCP port is reachable", details={"host": host, "port": port})

    async def send(self, config: dict[str, Any], payload: dict[str, Any], context: ConnectorContext) -> ConnectorSendResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorSendResult(success=False, error_code="INVALID_CONNECTOR_CONFIG", error_message="; ".join(validation.errors))

        zpl = _zpl_from_payload(payload)
        if not zpl:
            return ConnectorSendResult(success=False, error_code="ZPL_REQUIRED", error_message="payload.zpl must contain ZPL with ^XA and ^XZ")

        host = str(config["host"]).strip()
        port = int(config.get("port", 9100))
        timeout = float(config.get("timeout_seconds", 5))
        data = zpl.encode("utf-8")
        request_payload = _request_payload(config, payload, context, zpl)

        try:
            await asyncio.to_thread(_send_raw, host, port, data, timeout)
        except OSError as exc:
            return ConnectorSendResult(
                success=False,
                request_payload=request_payload,
                error_code="ZPL_PRINTER_SEND_FAILED",
                error_message=str(exc),
                external_error_message=str(exc),
                external_error_type="socket_error",
                human_title="Printer is unreachable",
                human_summary=f"Printer {host}:{port} rejected TCP send: {exc}",
                developer_message=str(exc),
                hint="Check printer power, network route, TCP port 9100 and firewall rules.",
                endpoint_url=f"tcp://{host}:{port}",
                operation="print_zpl",
            )

        return ConnectorSendResult(
            success=True,
            status_code=200,
            request_payload=request_payload,
            response_payload={
                "status": "sent_to_printer",
                "host": host,
                "port": port,
                "bytes_count": len(data),
                "zpl_sha256": hashlib.sha256(data).hexdigest(),
            },
        )

    async def dry_run_send(self, config: dict[str, Any], payload: dict[str, Any], context: ConnectorContext) -> ConnectorSendResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorSendResult(success=False, error_code="INVALID_CONNECTOR_CONFIG", error_message="; ".join(validation.errors))

        zpl = _zpl_from_payload(payload)
        if not zpl:
            return ConnectorSendResult(success=False, error_code="ZPL_REQUIRED", error_message="payload.zpl must contain ZPL with ^XA and ^XZ")

        data = zpl.encode("utf-8")
        return ConnectorSendResult(
            success=True,
            status_code=200,
            request_payload=_request_payload(config, payload, context, zpl),
            response_payload={
                "dry_run": True,
                "status": "would_send_to_printer",
                "host": str(config["host"]).strip(),
                "port": int(config.get("port", 9100)),
                "bytes_count": len(data),
                "zpl_sha256": hashlib.sha256(data).hexdigest(),
            },
        )

    async def cancel_print(self, config: dict[str, Any], payload: dict[str, Any], context: ConnectorContext, *, dry_run: bool = False) -> ConnectorSendResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorSendResult(success=False, error_code="INVALID_CONNECTOR_CONFIG", error_message="; ".join(validation.errors))

        command = str(config.get("cancel_command") or "~JA\n")
        host = str(config["host"]).strip()
        port = int(config.get("port", 9100))
        timeout = float(config.get("timeout_seconds", 5))
        data = command.encode("utf-8")
        request_payload = {
            "connector_type": "zpl_printer",
            "operation": "cancel_print",
            "host": host,
            "port": port,
            "printer_name": config.get("printer_name"),
            "job_id": payload.get("job_id"),
            "correlation_id": context.correlation_id,
            "bytes_count": len(data),
            "command": command.strip(),
        }
        if dry_run:
            return ConnectorSendResult(
                success=True,
                status_code=200,
                request_payload=request_payload,
                response_payload={"dry_run": True, "status": "would_send_cancel_to_printer", "host": host, "port": port, "command": command.strip()},
            )

        try:
            await asyncio.to_thread(_send_raw, host, port, data, timeout)
        except OSError as exc:
            return ConnectorSendResult(
                success=False,
                request_payload=request_payload,
                error_code="ZPL_PRINTER_CANCEL_FAILED",
                error_message=str(exc),
                external_error_message=str(exc),
                external_error_type="socket_error",
                human_title="Printer cancel command failed",
                human_summary=f"Printer {host}:{port} rejected cancel command: {exc}",
                developer_message=str(exc),
                hint="If the printer keeps printing, stop it manually and check network reachability before retrying.",
                endpoint_url=f"tcp://{host}:{port}",
                operation="cancel_print",
            )

        return ConnectorSendResult(
            success=True,
            status_code=200,
            request_payload=request_payload,
            response_payload={"status": "cancel_sent_to_printer", "host": host, "port": port, "bytes_count": len(data), "command": command.strip()},
        )

    async def receive(self, config: dict, context: ConnectorContext) -> list[ConnectorReceivedEvent]:
        return []


def _zpl_from_payload(payload: dict[str, Any]) -> str | None:
    value = payload.get("zpl")
    if not isinstance(value, str):
        return None
    zpl = value.strip()
    if "^XA" not in zpl or "^XZ" not in zpl:
        return None
    return zpl


def _request_payload(config: dict[str, Any], payload: dict[str, Any], context: ConnectorContext, zpl: str) -> dict[str, Any]:
    data = zpl.encode("utf-8")
    return {
        "connector_type": "zpl_printer",
        "host": str(config["host"]).strip(),
        "port": int(config.get("port", 9100)),
        "dpi": int(config.get("dpi", 203)),
        "printer_name": config.get("printer_name"),
        "job_id": payload.get("job_id"),
        "line_id": payload.get("line_id"),
        "correlation_id": context.correlation_id,
        "bytes_count": len(data),
        "zpl_sha256": hashlib.sha256(data).hexdigest(),
    }


def _send_raw(host: str, port: int, data: bytes, timeout: float) -> None:
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(data)


def _tcp_probe(host: str, port: int, timeout: float) -> tuple[bool, str | None]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, None
    except OSError as exc:
        return False, str(exc)


def _valid_host(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return bool(_HOSTNAME_RE.match(value))


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _positive_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
