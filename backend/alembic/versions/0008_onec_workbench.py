"""1c integration workbench

Revision ID: 0008_onec_workbench
Revises: 0007_printing
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_onec_workbench"
down_revision: str | None = "0007_printing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.Enum("inbound", "outbound", "internal", native_enum=False), nullable=False),
        sa.Column("source_system", sa.String(length=255), nullable=False),
        sa.Column("target_system", sa.String(length=255), nullable=True),
        sa.Column("message_type", sa.String(length=120), nullable=False),
        sa.Column("document_type", sa.String(length=120), nullable=True),
        sa.Column("document_number", sa.String(length=120), nullable=True),
        sa.Column("document_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.Enum("received", "parsed", "routed", "sent", "failed", "retry_waiting", "archived", native_enum=False), nullable=False),
        sa.Column("route_key", sa.String(length=255), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=False),
        sa.Column("payload_text", sa.Text(), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column("payload_size_bytes", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["integration_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["correlation_id", "direction", "event_id", "external_id", "message_type", "payload_sha256", "route_key", "source_system", "status", "target_system"]:
        op.create_index(op.f(f"ix_integration_messages_{column}"), "integration_messages", [column], unique=False)

    op.create_table(
        "operation_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("system_type", sa.String(length=100), nullable=False),
        sa.Column("operation", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("request_template_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("default_workflow_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["default_workflow_id"], ["workflows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_operation_templates_name"), "operation_templates", ["name"], unique=True)
    op.create_index(op.f("ix_operation_templates_operation"), "operation_templates", ["operation"], unique=False)
    op.create_index(op.f("ix_operation_templates_system_type"), "operation_templates", ["system_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_operation_templates_system_type"), table_name="operation_templates")
    op.drop_index(op.f("ix_operation_templates_operation"), table_name="operation_templates")
    op.drop_index(op.f("ix_operation_templates_name"), table_name="operation_templates")
    op.drop_table("operation_templates")
    for column in ["target_system", "status", "source_system", "route_key", "payload_sha256", "message_type", "external_id", "event_id", "direction", "correlation_id"]:
        op.drop_index(op.f(f"ix_integration_messages_{column}"), table_name="integration_messages")
    op.drop_table("integration_messages")
