"""enterprise runtime

Revision ID: 0012_enterprise_runtime
Revises: 0011_saved_test_cases
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_enterprise_runtime"
down_revision: str | None = "0011_saved_test_cases"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "integration_queue_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("connector_id", sa.Uuid(), nullable=True),
        sa.Column("workflow_id", sa.Uuid(), nullable=True),
        sa.Column("business_object", sa.String(length=120), nullable=False),
        sa.Column("operation", sa.String(length=160), nullable=False),
        sa.Column("current_step", sa.String(length=160), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("worker", sa.String(length=255), nullable=True),
        sa.Column("timeline_link", sa.String(length=500), nullable=True),
        sa.Column("payload_json", json_type(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["connector_instances.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["integration_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_id"], ["integration_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_integration_queue_status_priority", "integration_queue_messages", ["status", "priority", "next_retry_at"])
    for column in ("event_id", "message_id", "connector_id", "workflow_id", "business_object", "operation", "status", "priority", "worker", "next_retry_at"):
        op.create_index(op.f(f"ix_integration_queue_messages_{column}"), "integration_queue_messages", [column])

    op.create_table(
        "dead_letter_queue_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("queue_message_id", sa.Uuid(), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("message_id", sa.Uuid(), nullable=True),
        sa.Column("business_object", sa.String(length=120), nullable=False),
        sa.Column("operation", sa.String(length=160), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("payload_json", json_type(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
        sa.Column("restored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timeline_link", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["integration_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_id"], ["integration_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["queue_message_id"], ["integration_queue_messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("queue_message_id", "event_id", "message_id", "business_object", "operation", "archived"):
        op.create_index(op.f(f"ix_dead_letter_queue_items_{column}"), "dead_letter_queue_items", [column])

    op.create_table("canonical_business_objects", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(length=120), nullable=False), sa.Column("description", sa.Text(), nullable=True), sa.Column("schema_json", json_type(), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.PrimaryKeyConstraint("id"))
    op.create_index(op.f("ix_canonical_business_objects_name"), "canonical_business_objects", ["name"], unique=True)

    op.create_table("resolver_definitions", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(length=160), nullable=False), sa.Column("resolver_type", sa.String(length=40), nullable=False), sa.Column("business_object", sa.String(length=120), nullable=False), sa.Column("connector_id", sa.Uuid(), nullable=True), sa.Column("config_json", json_type(), nullable=False), sa.Column("cache_ttl_seconds", sa.Integer(), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.ForeignKeyConstraint(["connector_id"], ["connector_instances.id"], ondelete="SET NULL"), sa.PrimaryKeyConstraint("id"))
    for column in ("name", "resolver_type", "business_object"):
        op.create_index(op.f(f"ix_resolver_definitions_{column}"), "resolver_definitions", [column], unique=column == "name")

    op.create_table("business_rule_definitions", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(length=160), nullable=False), sa.Column("business_object", sa.String(length=120), nullable=True), sa.Column("operation", sa.String(length=160), nullable=True), sa.Column("status", sa.String(length=40), nullable=False), sa.Column("rules_json", json_type(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.PrimaryKeyConstraint("id"))
    for column in ("name", "business_object", "operation"):
        op.create_index(op.f(f"ix_business_rule_definitions_{column}"), "business_rule_definitions", [column], unique=column == "name")

    op.create_table("odata_cache_entries", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("resolver_name", sa.String(length=160), nullable=False), sa.Column("lookup_key", sa.String(length=500), nullable=False), sa.Column("status", sa.String(length=40), nullable=False), sa.Column("value_json", json_type(), nullable=True), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True), sa.Column("hit_count", sa.Integer(), nullable=False), sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("resolver_name", "lookup_key", name="uq_odata_cache_resolver_key"))
    for column in ("resolver_name", "lookup_key", "status", "expires_at"):
        op.create_index(op.f(f"ix_odata_cache_entries_{column}"), "odata_cache_entries", [column])


def downgrade() -> None:
    op.drop_table("odata_cache_entries")
    op.drop_table("business_rule_definitions")
    op.drop_table("resolver_definitions")
    op.drop_table("canonical_business_objects")
    op.drop_table("dead_letter_queue_items")
    op.drop_table("integration_queue_messages")
