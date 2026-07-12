from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class OperationProfile(TimestampMixin, Base):
    __tablename__ = "operation_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    connection_profile_id: Mapped[UUID | None] = mapped_column(ForeignKey("connector_instances.id", ondelete="SET NULL"), nullable=True, index=True)
    request_contract_id: Mapped[UUID | None] = mapped_column(ForeignKey("data_contracts.id", ondelete="SET NULL"), nullable=True, index=True)
    response_contract_id: Mapped[UUID | None] = mapped_column(ForeignKey("data_contracts.id", ondelete="SET NULL"), nullable=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    path: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    headers_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    body_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    request_template_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    request_template_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_body_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    success_condition_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    response_extractors_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON_TYPE, nullable=True)
    sample_request_json: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    sample_response_json: Mapped[dict[str, Any] | list[Any] | str | None] = mapped_column(JSON_TYPE, nullable=True)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags_json: Mapped[list[str] | None] = mapped_column(JSON_TYPE, nullable=True)
    package_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    last_test_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_test_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
