from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class OperationTemplate(TimestampMixin, Base):
    __tablename__ = "operation_templates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    system_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    request_template_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    response_schema_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    default_workflow_id: Mapped[UUID | None] = mapped_column(ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
