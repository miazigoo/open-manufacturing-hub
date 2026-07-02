from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import NotificationDeliveryStatus, NotificationTriggerType


class NotificationRuleCreate(BaseModel):
    name: str
    trigger_type: NotificationTriggerType
    filters: dict[str, Any] = Field(default_factory=dict)
    channels: list[dict[str, Any]] = Field(default_factory=list)
    cooldown_seconds: int = 600
    enabled: bool = True


class NotificationRulePatch(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    filters: dict[str, Any] | None = None
    channels: list[dict[str, Any]] | None = None
    cooldown_seconds: int | None = None


class NotificationRuleRead(BaseModel):
    id: UUID
    name: str
    enabled: bool
    trigger_type: NotificationTriggerType
    filters_json: dict[str, Any]
    channels_json: list[dict[str, Any]]
    cooldown_seconds: int
    last_triggered_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class NotificationDeliveryRead(BaseModel):
    id: UUID
    rule_id: UUID | None
    trigger_type: str
    target_channel: str
    target_address: str
    status: NotificationDeliveryStatus
    request_payload: dict[str, Any] | None
    response_payload: dict[str, Any] | None
    error_message: str | None
    sent_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
