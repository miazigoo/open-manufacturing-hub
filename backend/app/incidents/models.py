from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin, new_uuid
from app.core.enums import IncidentSeverity, IncidentStatus


class Incident(TimestampMixin, Base):
    __tablename__ = "incidents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    fingerprint: Mapped[str] = mapped_column(String(512), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=IncidentStatus.OPEN,
        nullable=False,
    )
    severity: Mapped[IncidentSeverity] = mapped_column(
        Enum(IncidentSeverity, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=IncidentSeverity.ERROR,
        nullable=False,
    )
    source_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failed_step: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_events_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    events: Mapped[list[IncidentEvent]] = relationship(back_populates="incident", cascade="all, delete-orphan", lazy="noload")


class IncidentEvent(TimestampMixin, Base):
    __tablename__ = "incident_events"
    __table_args__ = (Index("ix_incident_events_incident_event", "incident_id", "event_id", unique=True),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    incident_id: Mapped[UUID] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("integration_events.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[UUID | None] = mapped_column(ForeignKey("event_runs.id", ondelete="SET NULL"), nullable=True)
    step_id: Mapped[UUID | None] = mapped_column(ForeignKey("event_steps.id", ondelete="SET NULL"), nullable=True)

    incident: Mapped[Incident] = relationship(back_populates="events")
