from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid
from app.core.enums import EventStatus, RunMode, RunStatus, StepStatus

if TYPE_CHECKING:
    from app.artifacts.models import Artifact

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class IntegrationEvent(TimestampMixin, Base):
    __tablename__ = "integration_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_system: Mapped[str] = mapped_column(String(255), nullable=False)
    target_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=EventStatus.NEW,
        nullable=False,
    )
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    runs: Mapped[list[EventRun]] = relationship(back_populates="event", cascade="all, delete-orphan", lazy="selectin")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="event", lazy="selectin")


class EventRun(TimestampMixin, Base):
    __tablename__ = "event_runs"
    __table_args__ = (Index("ix_event_runs_event_run_number", "event_id", "run_number", unique=True),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("integration_events.id", ondelete="CASCADE"), nullable=False, index=True)
    run_number: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[RunMode] = mapped_column(
        Enum(RunMode, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False
    )
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=RunStatus.CREATED,
        nullable=False,
    )
    parent_run_id: Mapped[UUID | None] = mapped_column(ForeignKey("event_runs.id", ondelete="SET NULL"), nullable=True)
    workflow_id: Mapped[UUID | None] = mapped_column(ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True)
    workflow_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workflow_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mapping_versions_json: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    event: Mapped[IntegrationEvent] = relationship(back_populates="runs", foreign_keys=[event_id])
    parent_run: Mapped[EventRun | None] = relationship(remote_side=[id], foreign_keys=[parent_run_id])
    steps: Mapped[list[EventStep]] = relationship(back_populates="run", cascade="all, delete-orphan", lazy="selectin")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="run", lazy="selectin")


class EventStep(TimestampMixin, Base):
    __tablename__ = "event_steps"
    __table_args__ = (Index("ix_event_steps_run_step_order", "run_id", "step_order", unique=True),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("event_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[StepStatus] = mapped_column(
        Enum(StepStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=StepStatus.PENDING,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    step_config_json: Mapped[dict] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    condition: Mapped[str | None] = mapped_column(String(50), nullable=True)

    run: Mapped[EventRun] = relationship(back_populates="steps")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="step", lazy="selectin")
