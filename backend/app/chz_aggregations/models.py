from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class ChzAggregationRegistration(TimestampMixin, Base):
    __tablename__ = "chz_aggregation_registrations"
    __table_args__ = (
        Index("ix_chz_aggregation_reg_order", "order_number_1c"),
        Index("ix_chz_aggregation_reg_source", "source_system", "source_document_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    source_system: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_document_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    order_number_1c: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    order_number_external: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_codes: Mapped[int] = mapped_column(Integer, nullable=False)
    total_aggregates: Mapped[int] = mapped_column(Integer, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    forwarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
