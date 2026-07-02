from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class MappingDefinition(TimestampMixin, Base):
    __tablename__ = "mapping_definitions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_entity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_entity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    versions: Mapped[list[MappingVersion]] = relationship(
        back_populates="mapping", cascade="all, delete-orphan", lazy="selectin", order_by="MappingVersion.version"
    )


class MappingVersion(TimestampMixin, Base):
    __tablename__ = "mapping_versions"
    __table_args__ = (Index("ix_mapping_versions_mapping_version", "mapping_id", "version", unique=True),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    mapping_id: Mapped[UUID] = mapped_column(ForeignKey("mapping_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    rules_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON_TYPE, nullable=False)
    source_schema_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    target_schema_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    mapping: Mapped[MappingDefinition] = relationship(back_populates="versions")
