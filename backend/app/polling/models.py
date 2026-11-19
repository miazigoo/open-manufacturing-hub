from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid
from app.core.enums import PollingCursorType, PollingJobStatus

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class PollingJob(TimestampMixin, Base):
    __tablename__ = "polling_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    slug: Mapped[str | None] = mapped_column(String(160), nullable=True, unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_connector_id: Mapped[UUID] = mapped_column(ForeignKey("connector_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    integration_flow_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_flows.id", ondelete="SET NULL"), nullable=True, index=True)
    target_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    query_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entity_id_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    correlation_id_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at_field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cursor_value: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cursor_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    cursor_type: Mapped[PollingCursorType] = mapped_column(Enum(PollingCursorType, values_callable=lambda x: [e.value for e in x], native_enum=False), default=PollingCursorType.NONE, nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(40), default="interval_minutes", nullable=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[PollingJobStatus] = mapped_column(Enum(PollingJobStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), default=PollingJobStatus.IDLE, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    runs: Mapped[list["PollingJobRun"]] = relationship(back_populates="job", cascade="all, delete-orphan", lazy="noload")


class SourceEventCursor(TimestampMixin, Base):
    __tablename__ = "source_event_cursors"
    __table_args__ = (Index("ix_source_event_cursor_unique", "source_connector_id", "source_resource", "source_entity_id", "event_type", unique=True),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    source_connector_id: Mapped[UUID] = mapped_column(ForeignKey("connector_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    source_resource: Mapped[str] = mapped_column(String(255), nullable=False)
    source_entity_id: Mapped[str] = mapped_column(String(512), nullable=False)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    last_seen_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_event_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_events.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class PollingJobRun(TimestampMixin, Base):
    __tablename__ = "polling_job_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("polling_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[PollingJobStatus] = mapped_column(Enum(PollingJobStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False)
    items_read: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    events_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_events.id", ondelete="SET NULL"), nullable=True)
    cursor_before_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    cursor_after_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)

    job: Mapped["PollingJob"] = relationship(back_populates="runs")
