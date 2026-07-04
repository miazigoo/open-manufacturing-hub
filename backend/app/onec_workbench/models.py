from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid
from app.core.enums import IntegrationMessageDirection, IntegrationMessageStatus

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class IntegrationMessage(TimestampMixin, Base):
    __tablename__ = "integration_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    direction: Mapped[IntegrationMessageDirection] = mapped_column(Enum(IntegrationMessageDirection, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_system: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    message_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    document_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    document_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    document_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[IntegrationMessageStatus] = mapped_column(Enum(IntegrationMessageStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), default=IntegrationMessageStatus.RECEIVED, nullable=False, index=True)
    route_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    event_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_events.id", ondelete="SET NULL"), nullable=True, index=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
