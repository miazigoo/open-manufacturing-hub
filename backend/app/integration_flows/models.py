from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid
from app.core.enums import IntegrationFlowSourceType, IntegrationFlowTargetType

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class IntegrationFlow(TimestampMixin, Base):
    __tablename__ = "integration_flows"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_type: Mapped[IntegrationFlowSourceType] = mapped_column(Enum(IntegrationFlowSourceType, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False, index=True)
    target_type: Mapped[IntegrationFlowTargetType] = mapped_column(Enum(IntegrationFlowTargetType, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False, index=True)
    endpoint_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_endpoints.id", ondelete="SET NULL"), nullable=True, index=True)
    route_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_routes.id", ondelete="SET NULL"), nullable=True, index=True)
    workflow_id: Mapped[UUID | None] = mapped_column(ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True, index=True)
    compiled_workflow_id: Mapped[UUID | None] = mapped_column(ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True, index=True)
    mapping_id: Mapped[UUID | None] = mapped_column(ForeignKey("mapping_definitions.id", ondelete="SET NULL"), nullable=True, index=True)
    target_connector_id: Mapped[UUID | None] = mapped_column(ForeignKey("connector_instances.id", ondelete="SET NULL"), nullable=True, index=True)
    operation_template_id: Mapped[UUID | None] = mapped_column(ForeignKey("operation_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    matcher_group_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    action_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    response_config_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    builder_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    last_validation_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    compiled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    test_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    test_payload_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
