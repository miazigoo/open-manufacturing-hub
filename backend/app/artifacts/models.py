from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


def content_hash(content: dict[str, Any]) -> str:
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def content_size(content: dict[str, Any]) -> int:
    return len(json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8"))


class Artifact(TimestampMixin, Base):
    __tablename__ = "artifacts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("integration_events.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("event_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id: Mapped[UUID | None] = mapped_column(ForeignKey("event_steps.id", ondelete="SET NULL"), nullable=True, index=True)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    event = relationship("IntegrationEvent", back_populates="artifacts")
    run = relationship("EventRun", back_populates="artifacts")
    step = relationship("EventStep", back_populates="artifacts")
