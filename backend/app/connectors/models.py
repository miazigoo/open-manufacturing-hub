from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid
from app.core.enums import ConnectorDirection, ConnectorInstanceStatus, HealthStatus

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class ConnectorInstance(TimestampMixin, Base):
    __tablename__ = "connector_instances"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    connector_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    direction: Mapped[ConnectorDirection] = mapped_column(Enum(ConnectorDirection, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    status: Mapped[ConnectorInstanceStatus] = mapped_column(Enum(ConnectorInstanceStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), default=ConnectorInstanceStatus.UNKNOWN, nullable=False)
    last_health_status: Mapped[HealthStatus | None] = mapped_column(Enum(HealthStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=True)
    last_health_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_health_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
