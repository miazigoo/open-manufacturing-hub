"""data inbox templates and records

Revision ID: 0037_data_inbox
Revises: 0036_health_checks_idx
Create Date: 2026-08-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0037_data_inbox"
down_revision: str | None = "0036_health_checks_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "inbox_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("input_mode", sa.String(length=40), nullable=False, server_default="json"),
        sa.Column("schema_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("missing_policy", sa.String(length=40), nullable=False, server_default="reject"),
        sa.Column("storage_mode", sa.String(length=40), nullable=False, server_default="days"),
        sa.Column("storage_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("response_json", json_type(), nullable=True),
        sa.Column("auth_token", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inbox_templates_slug"), "inbox_templates", ["slug"], unique=True)
    op.create_table(
        "inbox_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("payload_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("fields_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("warnings_json", json_type(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("source_ip", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["inbox_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inbox_records_template_created", "inbox_records", ["template_id", "created_at"])
    op.create_index(op.f("ix_inbox_records_template_id"), "inbox_records", ["template_id"])
    op.create_index("ix_inbox_records_status", "inbox_records", ["status"])


def downgrade() -> None:
    op.drop_index("ix_inbox_records_status", table_name="inbox_records")
    op.drop_index(op.f("ix_inbox_records_template_id"), table_name="inbox_records")
    op.drop_index("ix_inbox_records_template_created", table_name="inbox_records")
    op.drop_table("inbox_records")
    op.drop_index(op.f("ix_inbox_templates_slug"), table_name="inbox_templates")
    op.drop_table("inbox_templates")
