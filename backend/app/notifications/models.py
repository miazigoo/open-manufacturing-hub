from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid
from app.core.enums import NotificationDeliveryStatus, NotificationTriggerType

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class NotificationRule(TimestampMixin, Base):
    __tablename__ = "notification_rules"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    trigger_type: Mapped[NotificationTriggerType] = mapped_column(Enum(NotificationTriggerType, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    channels_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=600, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class NotificationDelivery(TimestampMixin, Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    rule_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    trigger_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_channel: Mapped[str] = mapped_column(String(100), nullable=False)
    target_address: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[NotificationDeliveryStatus] = mapped_column(Enum(NotificationDeliveryStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False)
    request_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
