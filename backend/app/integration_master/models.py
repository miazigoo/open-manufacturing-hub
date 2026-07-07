from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class IntegrationMasterDraft(TimestampMixin, Base):
    __tablename__ = "integration_master_drafts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    scenario_key: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    input_mode: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    contract_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    parse_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
