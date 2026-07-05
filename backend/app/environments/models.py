from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class EnvironmentType(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"
    CUSTOM = "custom"


class EnvironmentProfile(TimestampMixin, Base):
    __tablename__ = "environments"
    __table_args__ = (
        UniqueConstraint("name", name="uq_environments_name"),
        UniqueConstraint("code", name="uq_environments_code"),
        Index("ix_environments_current", "is_current"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    environment_type: Mapped[EnvironmentType] = mapped_column(Enum(EnvironmentType, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    variables: Mapped[list[EnvironmentVariable]] = relationship(back_populates="environment", cascade="all, delete-orphan", lazy="selectin")


class EnvironmentVariable(TimestampMixin, Base):
    __tablename__ = "environment_variables"
    __table_args__ = (
        UniqueConstraint("environment_id", "key", name="uq_environment_variables_environment_key"),
        Index("ix_environment_variables_key", "key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    environment_id: Mapped[UUID] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(160), nullable=False)
    value_json: Mapped[dict[str, Any] | str | int | float | bool | list[Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    secret_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    environment: Mapped[EnvironmentProfile] = relationship(back_populates="variables")
