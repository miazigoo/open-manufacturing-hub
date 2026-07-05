from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class ConfigVersionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
    ROLLBACK = "rollback"
    REJECTED = "rejected"


class ConfigVersionTestStatus(StrEnum):
    NOT_TESTED = "not_tested"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


class ConfigVersion(TimestampMixin, Base):
    __tablename__ = "config_versions"
    __table_args__ = (
        UniqueConstraint("object_type", "object_id", "version_number", name="uq_config_versions_object_version"),
        Index("ix_config_versions_object", "object_type", "object_id"),
        Index("ix_config_versions_status", "status"),
        Index(
            "uq_config_versions_effective_active",
            "object_type",
            "object_id",
            unique=True,
            postgresql_where=text("status in ('active', 'rollback')"),
            sqlite_where=text("status in ('active', 'rollback')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    object_type: Mapped[str] = mapped_column(String(80), nullable=False)
    object_id: Mapped[UUID] = mapped_column(nullable=False)
    object_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ConfigVersionStatus] = mapped_column(Enum(ConfigVersionStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rollback_of_version_id: Mapped[UUID | None] = mapped_column(ForeignKey("config_versions.id", ondelete="SET NULL"), nullable=True)
    test_status: Mapped[ConfigVersionTestStatus] = mapped_column(Enum(ConfigVersionTestStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), default=ConfigVersionTestStatus.NOT_TESTED, nullable=False)
    last_test_event_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_events.id", ondelete="SET NULL"), nullable=True)
    last_test_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
