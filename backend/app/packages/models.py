from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid
from app.core.enums import IntegrationPackageStatus

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class InstalledPackage(TimestampMixin, Base):
    __tablename__ = "installed_packages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    package_id: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[IntegrationPackageStatus] = mapped_column(Enum(IntegrationPackageStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), default=IntegrationPackageStatus.ENABLED, nullable=False, index=True)
    official: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, nullable=False)
    install_log_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON_TYPE, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class PackageRuntimeCapability(TimestampMixin, Base):
    __tablename__ = "package_runtime_capabilities"
    __table_args__ = (UniqueConstraint("package_id", "capability_type", "capability_code", name="uq_package_runtime_capability"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    package_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    capability_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    capability_code: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=True)
