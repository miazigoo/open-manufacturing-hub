from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.enums import ConnectorDirection, HealthStatus
from app.sdk.types import ConnectorConfigValidationResult, ConnectorContext, ConnectorHealthResult, ConnectorReceivedEvent, ConnectorSendResult


class SMBShareConnector:
    connector_type = "smb_share"
    display_name = "SMB Share"
    direction = ConnectorDirection.TARGET

    async def validate_config(self, config: dict[str, Any]) -> ConnectorConfigValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        unc_path = str(config.get("unc_path") or config.get("path") or "").strip()
        if not unc_path:
            errors.append("unc_path is required")
        elif not (unc_path.startswith("\\\\") or unc_path.startswith("smb://")):
            errors.append("unc_path must start with \\\\server\\share or smb://server/share")
        if config.get("password") and not isinstance(config.get("password"), (str, dict)):
            errors.append("password must be a string or secret reference")
        if config.get("username") and not isinstance(config.get("username"), str):
            errors.append("username must be a string")
        if config.get("password") and isinstance(config.get("password"), str):
            warnings.append("Use Secrets Store references for SMB passwords in production configs.")
        return ConnectorConfigValidationResult(valid=not errors, errors=errors, warnings=warnings)

    async def healthcheck(self, config: dict[str, Any]) -> ConnectorHealthResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorHealthResult(status=HealthStatus.WARNING, message="Invalid SMB share config", details={"errors": validation.errors})
        return ConnectorHealthResult(status=HealthStatus.UNKNOWN, message="SMB share configured; write probe requires explicit confirmation", details={"unc_path": config.get("unc_path") or config.get("path")})

    async def send(self, config: dict[str, Any], payload: dict[str, Any], context: ConnectorContext) -> ConnectorSendResult:
        return await self.dry_run_send(config, payload, context)

    async def dry_run_send(self, config: dict[str, Any], payload: dict[str, Any], context: ConnectorContext) -> ConnectorSendResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorSendResult(success=False, error_code="INVALID_CONNECTOR_CONFIG", error_message="; ".join(validation.errors))
        return ConnectorSendResult(
            success=True,
            status_code=200,
            request_payload={"connector_type": self.connector_type, "unc_path": config.get("unc_path") or config.get("path"), "dry_run": True},
            response_payload={"dry_run": True, "status": "would_write_to_smb_share", "file_name": payload.get("file_name")},
        )

    async def receive(self, config: dict[str, Any], context: ConnectorContext) -> list[ConnectorReceivedEvent]:
        return []


class LocalDirectoryConnector:
    connector_type = "local_directory"
    display_name = "Local Directory"
    direction = ConnectorDirection.TARGET

    async def validate_config(self, config: dict[str, Any]) -> ConnectorConfigValidationResult:
        errors: list[str] = []
        path = str(config.get("path") or config.get("directory") or "").strip()
        if not path:
            errors.append("path is required")
        elif "\x00" in path:
            errors.append("path contains invalid null byte")
        if config.get("create_if_missing") is not None and not isinstance(config.get("create_if_missing"), bool):
            errors.append("create_if_missing must be boolean")
        if config.get("allow_overwrite") is not None and not isinstance(config.get("allow_overwrite"), bool):
            errors.append("allow_overwrite must be boolean")
        return ConnectorConfigValidationResult(valid=not errors, errors=errors)

    async def healthcheck(self, config: dict[str, Any]) -> ConnectorHealthResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorHealthResult(status=HealthStatus.WARNING, message="Invalid local directory config", details={"errors": validation.errors})
        directory = Path(str(config.get("path") or config.get("directory"))).expanduser()
        exists = directory.exists()
        writable = directory.is_dir() and _is_writable(directory)
        status = HealthStatus.OK if exists and writable else HealthStatus.WARNING
        message = "Local directory is writable" if exists and writable else "Local directory is not writable or does not exist"
        return ConnectorHealthResult(status=status, message=message, details={"path": str(directory), "exists": exists, "writable": writable})

    async def send(self, config: dict[str, Any], payload: dict[str, Any], context: ConnectorContext) -> ConnectorSendResult:
        return await self.dry_run_send(config, payload, context)

    async def dry_run_send(self, config: dict[str, Any], payload: dict[str, Any], context: ConnectorContext) -> ConnectorSendResult:
        validation = await self.validate_config(config)
        if not validation.valid:
            return ConnectorSendResult(success=False, error_code="INVALID_CONNECTOR_CONFIG", error_message="; ".join(validation.errors))
        path = str(config.get("path") or config.get("directory"))
        return ConnectorSendResult(
            success=True,
            status_code=200,
            request_payload={"connector_type": self.connector_type, "path": path, "dry_run": True},
            response_payload={"dry_run": True, "status": "would_write_to_local_directory", "file_name": payload.get("file_name")},
        )

    async def receive(self, config: dict[str, Any], context: ConnectorContext) -> list[ConnectorReceivedEvent]:
        return []


def _is_writable(directory: Path) -> bool:
    try:
        probe = directory / ".omh-write-probe"
        with probe.open("w", encoding="utf-8") as handle:
            handle.write("ok")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False
