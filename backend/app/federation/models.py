from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class FederationSyncRun(TimestampMixin, Base):
    __tablename__ = "federation_sync_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    direction: Mapped[str] = mapped_column(String(40), default="pull", nullable=False)
    center_url: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    version: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
