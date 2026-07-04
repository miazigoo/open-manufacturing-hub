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


class IntegrationEndpoint(TimestampMixin, Base):
    __tablename__ = "integration_endpoints"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    response_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    default_source_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_target_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    default_entity_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workflow_id: Mapped[UUID | None] = mapped_column(ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True)
    route_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_routes.id", ondelete="SET NULL"), nullable=True)
    operation_template_id: Mapped[UUID | None] = mapped_column(ForeignKey("operation_templates.id", ondelete="SET NULL"), nullable=True)
    auth_mode: Mapped[str] = mapped_column(String(40), default="none", nullable=False)
    auth_config_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class IntegrationRoute(TimestampMixin, Base):
    __tablename__ = "integration_routes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_system: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    target_system: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    event_type: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    message_type: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    document_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    operation: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    condition_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    workflow_id: Mapped[UUID | None] = mapped_column(ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True)
    mapping_id: Mapped[UUID | None] = mapped_column(ForeignKey("mapping_definitions.id", ondelete="SET NULL"), nullable=True)
    target_connector_id: Mapped[UUID | None] = mapped_column(ForeignKey("connector_instances.id", ondelete="SET NULL"), nullable=True)
    operation_template_id: Mapped[UUID | None] = mapped_column(ForeignKey("operation_templates.id", ondelete="SET NULL"), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ODataLookupTemplate(TimestampMixin, Base):
    __tablename__ = "odata_lookup_templates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    connector_id: Mapped[UUID] = mapped_column(ForeignKey("connector_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    filter_template: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    extract_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cache_ttl_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
