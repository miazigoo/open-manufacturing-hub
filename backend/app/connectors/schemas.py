from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import ConnectorDirection, ConnectorInstanceStatus, HealthStatus


class ConnectorTypeRead(BaseModel):
    connector_type: str
    display_name: str
    direction: ConnectorDirection


class ConnectorInstanceCreate(BaseModel):
    name: str
    connector_type: str
    direction: ConnectorDirection
    enabled: bool = True
    config_json: dict[str, Any] = {}


class ConnectorInstancePatch(BaseModel):
    name: str | None = None
    direction: ConnectorDirection | None = None
    enabled: bool | None = None
    config_json: dict[str, Any] | None = None
    status: ConnectorInstanceStatus | None = None


class ConnectorInstanceRead(BaseModel):
    id: UUID
    name: str
    connector_type: str
    direction: ConnectorDirection
    enabled: bool
    config_json: dict[str, Any]
    status: ConnectorInstanceStatus
    last_health_status: HealthStatus | None
    last_health_message: str | None
    last_health_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConnectorConfigValidationRead(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]


class ConnectorHealthRead(BaseModel):
    status: HealthStatus
    message: str
    details: dict[str, Any]
    checked_at: datetime


class WebhookEventResponse(BaseModel):
    event_id: UUID
    status: str
