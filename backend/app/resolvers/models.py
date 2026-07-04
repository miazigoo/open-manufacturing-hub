from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class ResolverDefinitionV2(TimestampMixin, Base):
    __tablename__ = "resolver_definitions_v2"
    __table_args__ = (
        UniqueConstraint("resolver_code", name="uq_resolver_definitions_v2_code"),
        UniqueConstraint("name", name="uq_resolver_definitions_v2_name"),
        Index("ix_resolver_definitions_v2_object_strategy", "object_type", "strategy"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    resolver_code: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    strategy: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    connector_id: Mapped[UUID | None] = mapped_column(ForeignKey("connector_instances.id", ondelete="SET NULL"), nullable=True, index=True)
    input_schema_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    output_schema_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    cache_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cache_ttl_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ResolverCacheEntry(TimestampMixin, Base):
    __tablename__ = "resolver_cache_entries"
    __table_args__ = (
        UniqueConstraint("resolver_id", "cache_key", name="uq_resolver_cache_resolver_key"),
        Index("ix_resolver_cache_code_key", "resolver_code", "cache_key"),
        Index("ix_resolver_cache_object_expires", "object_type", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    resolver_id: Mapped[UUID] = mapped_column(ForeignKey("resolver_definitions_v2.id", ondelete="CASCADE"), nullable=False, index=True)
    resolver_code: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    cache_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    resolved_object_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    source_connector_id: Mapped[UUID | None] = mapped_column(ForeignKey("connector_instances.id", ondelete="SET NULL"), nullable=True, index=True)
    source_system: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
