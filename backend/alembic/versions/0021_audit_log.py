"""audit log change history

Revision ID: 0021_audit_log
Revises: 0020_production_safety
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0021_audit_log"
down_revision: str | None = "0020_production_safety"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_username", sa.String(length=255), nullable=True),
        sa.Column("actor_display_name", sa.String(length=255), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("source_ip", sa.String(length=120), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("object_type", sa.String(length=120), nullable=True),
        sa.Column("object_id", sa.String(length=160), nullable=True),
        sa.Column("object_name", sa.String(length=255), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("details_json", json_type(), nullable=True),
        sa.Column("before_json", json_type(), nullable=True),
        sa.Column("after_json", json_type(), nullable=True),
        sa.Column("diff_json", json_type(), nullable=True),
        sa.Column("request_id", sa.String(length=120), nullable=True),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("queue_item_id", sa.Uuid(), nullable=True),
        sa.Column("package_id", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["timestamp", "actor_user_id", "actor_username", "actor_type", "action", "category", "severity", "object_type", "object_id", "request_id", "correlation_id", "event_id", "queue_item_id", "package_id"]:
        op.create_index(op.f(f"ix_audit_events_{column}"), "audit_events", [column], unique=False)
    op.create_index("ix_audit_events_object", "audit_events", ["object_type", "object_id"], unique=False)
    op.create_index("ix_audit_events_actor", "audit_events", ["actor_user_id", "actor_username"], unique=False)
    op.create_index("ix_audit_events_category_action", "audit_events", ["category", "action"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_audit_events_category_action", table_name="audit_events")
    op.drop_index("ix_audit_events_actor", table_name="audit_events")
    op.drop_index("ix_audit_events_object", table_name="audit_events")
    for column in ["package_id", "queue_item_id", "event_id", "correlation_id", "request_id", "object_id", "object_type", "severity", "category", "action", "actor_type", "actor_username", "actor_user_id", "timestamp"]:
        op.drop_index(op.f(f"ix_audit_events_{column}"), table_name="audit_events")
    op.drop_table("audit_events")
