from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, new_uuid
from app.core.enums import AuditActorType, AuditSeverity

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_object", "object_type", "object_id"),
        Index("ix_audit_events_actor", "actor_user_id", "actor_username"),
        Index("ix_audit_events_category_action", "category", "action"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    actor_user_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    actor_username: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    actor_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor_type: Mapped[AuditActorType] = mapped_column(Enum(AuditActorType, values_callable=lambda x: [e.value for e in x], native_enum=False), default=AuditActorType.UNKNOWN, nullable=False, index=True)
    source_ip: Mapped[str | None] = mapped_column(String(120), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severity: Mapped[AuditSeverity] = mapped_column(Enum(AuditSeverity, values_callable=lambda x: [e.value for e in x], native_enum=False), default=AuditSeverity.INFO, nullable=False, index=True)
    object_type: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    object_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    object_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    before_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    diff_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    event_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    queue_item_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    package_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
