from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class MappingProfile(TimestampMixin, Base):
    __tablename__ = "mapping_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    source_context_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    target_contract_id: Mapped[UUID | None] = mapped_column(ForeignKey("data_contracts.id", ondelete="SET NULL"), nullable=True, index=True)
    operation_profile_id: Mapped[UUID | None] = mapped_column(ForeignKey("operation_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    mapping_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    package_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )
