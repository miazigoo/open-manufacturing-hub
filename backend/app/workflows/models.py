from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class Workflow(TimestampMixin, Base):
    __tablename__ = "workflows"
    __table_args__ = (
        Index("ix_workflows_trigger", "event_type", "source_system", "target_system", "enabled"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_system: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    target_system: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    steps_json: Mapped[list[str]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    validation_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    source_mapping_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("mapping_versions.id", ondelete="SET NULL"), nullable=True)
    target_mapping_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("mapping_versions.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    source_mapping_version = relationship("MappingVersion", foreign_keys=[source_mapping_version_id], lazy="selectin")
    target_mapping_version = relationship("MappingVersion", foreign_keys=[target_mapping_version_id], lazy="selectin")
