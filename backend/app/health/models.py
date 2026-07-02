from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid
from app.core.enums import HealthComponentType, HealthStatus

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class Site(TimestampMixin, Base):
    __tablename__ = "sites"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    checks: Mapped[list[HealthCheck]] = relationship(back_populates="site", lazy="selectin")


class HealthCheck(TimestampMixin, Base):
    __tablename__ = "health_checks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    component_type: Mapped[HealthComponentType] = mapped_column(Enum(HealthComponentType, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False)
    component_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    site_id: Mapped[UUID | None] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[HealthStatus] = mapped_column(Enum(HealthStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False)
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    site: Mapped[Site | None] = relationship(back_populates="checks")


class AgentHeartbeat(Base):
    __tablename__ = "agent_heartbeats"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    site_id: Mapped[UUID] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    internet_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    can_reach_hub: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    can_reach_wms: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    can_reach_erp: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    local_ip: Mapped[str | None] = mapped_column(String(100), nullable=True)
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
