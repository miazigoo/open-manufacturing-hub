from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class ExternalErrorRecord(Base):
    __tablename__ = "external_error_records"
    __table_args__ = (
        Index("ix_external_error_records_event_created", "event_id", "created_at"),
        Index("ix_external_error_records_incident_created", "incident_id", "created_at"),
        Index("ix_external_error_records_step", "step_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    event_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_events.id", ondelete="CASCADE"), nullable=True, index=True)
    run_id: Mapped[UUID | None] = mapped_column(ForeignKey("event_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    step_id: Mapped[UUID | None] = mapped_column(ForeignKey("event_steps.id", ondelete="SET NULL"), nullable=True, index=True)
    incident_id: Mapped[UUID | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"), nullable=True, index=True)

    source_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    connector_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    connector_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    operation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    endpoint_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    http_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)

    normalized_code: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_message: Mapped[str] = mapped_column(Text, nullable=False)
    human_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    human_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    developer_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)

    external_error_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_error_type: Mapped[str | None] = mapped_column(String(120), nullable=True)

    response_content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    response_body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_body_json: Mapped[object | None] = mapped_column(JSON_TYPE, nullable=True)
    response_body_xml: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_body_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_body_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    request_artifact_id: Mapped[UUID | None] = mapped_column(ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True)
    response_artifact_id: Mapped[UUID | None] = mapped_column(ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True)
    error_artifact_id: Mapped[UUID | None] = mapped_column(ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
