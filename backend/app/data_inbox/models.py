from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class InboxTemplate(TimestampMixin, Base):
    __tablename__ = "inbox_templates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    input_mode: Mapped[str] = mapped_column(String(40), default="json", nullable=False)
    schema_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    missing_policy: Mapped[str] = mapped_column(String(40), default="reject", nullable=False)
    storage_mode: Mapped[str] = mapped_column(String(40), default="days", nullable=False)
    storage_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    response_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    auth_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    records: Mapped[list["InboxRecord"]] = relationship(back_populates="template", cascade="all, delete-orphan", lazy="noload")


class InboxRecord(TimestampMixin, Base):
    __tablename__ = "inbox_records"
    __table_args__ = (
        Index("ix_inbox_records_template_created", "template_id", "created_at"),
        Index("ix_inbox_records_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    template_id: Mapped[UUID] = mapped_column(ForeignKey("inbox_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    fields_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    warnings_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    source_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)

    template: Mapped[InboxTemplate] = relationship(back_populates="records")
