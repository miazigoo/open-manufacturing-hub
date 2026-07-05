from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class ChangeSetStatus(StrEnum):
    DRAFT = "draft"
    EXPORTED = "exported"
    IMPORT_PREVIEWED = "import_previewed"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ChangeSetOperation(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    ENABLE = "enable"
    DISABLE = "disable"
    DELETE_DISABLED_IN_MVP = "delete_disabled_in_mvp"


class ChangeSet(TimestampMixin, Base):
    __tablename__ = "change_sets"
    __table_args__ = (Index("ix_change_sets_status", "status"), Index("ix_change_sets_created_at", "created_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_environment: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    target_environment: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    status: Mapped[ChangeSetStatus] = mapped_column(Enum(ChangeSetStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), default=ChangeSetStatus.DRAFT, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)

    items: Mapped[list[ChangeSetItem]] = relationship(back_populates="change_set", cascade="all, delete-orphan", lazy="selectin", order_by="ChangeSetItem.created_at")


class ChangeSetItem(TimestampMixin, Base):
    __tablename__ = "change_set_items"
    __table_args__ = (Index("ix_change_set_items_change_set", "change_set_id"), Index("ix_change_set_items_object", "object_type", "object_id"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    change_set_id: Mapped[UUID] = mapped_column(ForeignKey("change_sets.id", ondelete="CASCADE"), nullable=False)
    object_type: Mapped[str] = mapped_column(String(80), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    object_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    operation: Mapped[ChangeSetOperation] = mapped_column(Enum(ChangeSetOperation, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    version_id: Mapped[UUID | None] = mapped_column(ForeignKey("config_versions.id", ondelete="SET NULL"), nullable=True)
    package_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    dependencies_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)

    change_set: Mapped[ChangeSet] = relationship(back_populates="items")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
