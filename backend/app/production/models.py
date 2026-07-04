from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid
from app.core.enums import BackupStatus, BackupType

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class BackupRecord(TimestampMixin, Base):
    __tablename__ = "backup_records"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    backup_type: Mapped[BackupType] = mapped_column(Enum(BackupType, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False, index=True)
    status: Mapped[BackupStatus] = mapped_column(Enum(BackupStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False, index=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)


class ProductionState(TimestampMixin, Base):
    __tablename__ = "production_state"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default="default")
    update_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    update_mode_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    update_mode_enabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    update_mode_enabled_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
