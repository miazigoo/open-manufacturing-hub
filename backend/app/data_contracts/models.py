from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class DataContract(TimestampMixin, Base):
    __tablename__ = "data_contracts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    owner_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    owner_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    example_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )
