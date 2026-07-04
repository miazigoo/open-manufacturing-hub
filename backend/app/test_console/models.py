from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class SavedTestCase(TimestampMixin, Base):
    __tablename__ = "saved_test_cases"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    endpoint_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_endpoints.id", ondelete="SET NULL"), nullable=True, index=True)
    method: Mapped[str] = mapped_column(String(16), default="POST", nullable=False)
    headers_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    input_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    expected_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_run_event_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_events.id", ondelete="SET NULL"), nullable=True)
    last_run_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
