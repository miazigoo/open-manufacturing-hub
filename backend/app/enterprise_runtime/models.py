from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid
from app.core.enums import BusinessRuleStatus, EnterpriseQueueStatus, ODataCacheStatus, ResolverType

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class IntegrationQueueMessage(TimestampMixin, Base):
    __tablename__ = "integration_queue_messages"
    __table_args__ = (
        Index("ix_integration_queue_status_priority", "status", "priority", "next_retry_at"),
        Index("ix_integration_queue_business_key", "business_object", "business_key"),
        Index("ix_integration_queue_lock", "status", "locked_until"),
        Index("ix_integration_queue_event_created", "event_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    event_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_events.id", ondelete="SET NULL"), nullable=True, index=True)
    message_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_messages.id", ondelete="SET NULL"), nullable=True, index=True)
    run_id: Mapped[UUID | None] = mapped_column(ForeignKey("event_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    flow_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_flows.id", ondelete="SET NULL"), nullable=True, index=True)
    endpoint_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_endpoints.id", ondelete="SET NULL"), nullable=True, index=True)
    route_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_routes.id", ondelete="SET NULL"), nullable=True, index=True)
    connector_id: Mapped[UUID | None] = mapped_column(ForeignKey("connector_instances.id", ondelete="SET NULL"), nullable=True, index=True)
    workflow_id: Mapped[UUID | None] = mapped_column(ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True, index=True)
    business_object: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    business_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    source_system: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    target_system: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    connector_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    current_step: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[EnterpriseQueueStatus] = mapped_column(Enum(EnterpriseQueueStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), default=EnterpriseQueueStatus.WAITING, nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False, index=True)
    worker: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    locked_by: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    timeline_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    original_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_external_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class DeadLetterQueueItem(TimestampMixin, Base):
    __tablename__ = "dead_letter_queue_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    queue_message_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_queue_messages.id", ondelete="SET NULL"), nullable=True, index=True)
    event_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_events.id", ondelete="SET NULL"), nullable=True, index=True)
    message_id: Mapped[UUID | None] = mapped_column(ForeignKey("integration_messages.id", ondelete="SET NULL"), nullable=True, index=True)
    business_object: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    current_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timeline_link: Mapped[str | None] = mapped_column(String(500), nullable=True)


class QueueAttempt(TimestampMixin, Base):
    __tablename__ = "queue_attempts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    queue_message_id: Mapped[UUID] = mapped_column(ForeignKey("integration_queue_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    run_id: Mapped[UUID | None] = mapped_column(ForeignKey("event_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_error_record_id: Mapped[UUID | None] = mapped_column(ForeignKey("external_error_records.id", ondelete="SET NULL"), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class CanonicalBusinessObject(TimestampMixin, Base):
    __tablename__ = "canonical_business_objects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ResolverDefinition(TimestampMixin, Base):
    __tablename__ = "resolver_definitions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    resolver_type: Mapped[ResolverType] = mapped_column(Enum(ResolverType, values_callable=lambda x: [e.value for e in x], native_enum=False), nullable=False, index=True)
    business_object: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    connector_id: Mapped[UUID | None] = mapped_column(ForeignKey("connector_instances.id", ondelete="SET NULL"), nullable=True)
    config_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    cache_ttl_seconds: Mapped[int] = mapped_column(Integer, default=3600, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class BusinessRuleDefinition(TimestampMixin, Base):
    __tablename__ = "business_rule_definitions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    business_object: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    operation: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    status: Mapped[BusinessRuleStatus] = mapped_column(Enum(BusinessRuleStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), default=BusinessRuleStatus.ENABLED, nullable=False)
    rules_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON_TYPE, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class ODataCacheEntry(TimestampMixin, Base):
    __tablename__ = "odata_cache_entries"
    __table_args__ = (UniqueConstraint("resolver_name", "lookup_key", name="uq_odata_cache_resolver_key"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    resolver_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    lookup_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    status: Mapped[ODataCacheStatus] = mapped_column(Enum(ODataCacheStatus, values_callable=lambda x: [e.value for e in x], native_enum=False), default=ODataCacheStatus.MISS, nullable=False, index=True)
    value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON_TYPE, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_hit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
