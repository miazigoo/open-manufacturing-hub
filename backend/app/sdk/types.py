from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.core.enums import ConnectorDirection, HealthStatus


@dataclass(slots=True)
class ConnectorContext:
    event_id: UUID | None = None
    run_id: UUID | None = None
    step_id: UUID | None = None
    correlation_id: str | None = None
    source_system: str | None = None
    target_system: str | None = None
    dry_run: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConnectorHealthResult:
    status: HealthStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class ConnectorSendResult:
    success: bool
    status_code: int | None = None
    response_payload: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    request_payload: dict[str, Any] | None = None
    external_error_code: str | None = None
    external_error_message: str | None = None
    external_error_type: str | None = None
    developer_message: str | None = None
    human_title: str | None = None
    human_summary: str | None = None
    hint: str | None = None
    raw_response_text: str | None = None
    raw_response_json: dict[str, Any] | list[Any] | None = None
    raw_response_xml: str | None = None
    response_headers: dict[str, Any] | None = None
    response_content_type: str | None = None
    endpoint_url: str | None = None
    operation: str | None = None
    connector_type: str | None = None
    connector_name: str | None = None


@dataclass(slots=True)
class ConnectorReceivedEvent:
    source_system: str
    target_system: str | None
    event_type: str
    entity_type: str | None
    entity_id: str | None
    payload: dict[str, Any]
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ConnectorConfigValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ConnectorMetadata:
    connector_type: str
    display_name: str
    direction: ConnectorDirection
