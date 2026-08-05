from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class MarkingCodePoolExport(TimestampMixin, Base):
    __tablename__ = "marking_code_pool_exports"
    __table_args__ = (
        Index("ix_marking_code_pool_exports_source_document", "source_system", "source_document_id"),
        Index("ix_marking_code_pool_exports_file_name", "file_name"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    source_system: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_document_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_document_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_number: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    total_codes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    forwarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MarkingCodePoolRoutingRule(TimestampMixin, Base):
    __tablename__ = "marking_code_pool_routing_rules"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    match_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    targets_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON_TYPE, default=list, nullable=False)
