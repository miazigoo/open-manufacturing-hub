"""queue first runtime

Revision ID: 0016_queue_first_runtime
Revises: 0015_integration_packages
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_queue_first_runtime"
down_revision: str | None = "0015_integration_packages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.add_column("integration_endpoints", sa.Column("processing_mode", sa.String(length=40), server_default="async_queue", nullable=False))

    for name, column in [
        ("run_id", sa.Column("run_id", sa.Uuid(), nullable=True)),
        ("flow_id", sa.Column("flow_id", sa.Uuid(), nullable=True)),
        ("endpoint_id", sa.Column("endpoint_id", sa.Uuid(), nullable=True)),
        ("route_id", sa.Column("route_id", sa.Uuid(), nullable=True)),
        ("business_key", sa.Column("business_key", sa.String(length=255), nullable=True)),
        ("source_system", sa.Column("source_system", sa.String(length=255), nullable=True)),
        ("target_system", sa.Column("target_system", sa.String(length=255), nullable=True)),
        ("connector_name", sa.Column("connector_name", sa.String(length=255), nullable=True)),
        ("locked_by", sa.Column("locked_by", sa.String(length=255), nullable=True)),
        ("original_payload_json", sa.Column("original_payload_json", json_type(), server_default=sa.text("'{}'::jsonb"), nullable=False)),
        ("last_error_code", sa.Column("last_error_code", sa.String(length=255), nullable=True)),
        ("last_error_message", sa.Column("last_error_message", sa.Text(), nullable=True)),
        ("last_external_error_message", sa.Column("last_external_error_message", sa.Text(), nullable=True)),
        ("locked_until", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True)),
        ("started_at", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True)),
        ("finished_at", sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True)),
    ]:
        op.add_column("integration_queue_messages", column)
        if name not in {"original_payload_json", "started_at", "finished_at", "last_error_message", "last_external_error_message"}:
            op.create_index(op.f(f"ix_integration_queue_messages_{name}"), "integration_queue_messages", [name])

    op.create_foreign_key(None, "integration_queue_messages", "event_runs", ["run_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(None, "integration_queue_messages", "integration_flows", ["flow_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(None, "integration_queue_messages", "integration_endpoints", ["endpoint_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(None, "integration_queue_messages", "integration_routes", ["route_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_integration_queue_business_key", "integration_queue_messages", ["business_object", "business_key"])
    op.create_index("ix_integration_queue_lock", "integration_queue_messages", ["status", "locked_until"])

    op.add_column("dead_letter_queue_items", sa.Column("current_payload_json", json_type(), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.add_column("dead_letter_queue_items", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column("dead_letter_queue_items", sa.Column("attempts", sa.Integer(), server_default="0", nullable=False))

    op.create_table(
        "queue_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("queue_message_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("external_error_record_id", sa.Uuid(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["external_error_record_id"], ["external_error_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["queue_message_id"], ["integration_queue_messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["event_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("queue_message_id", "run_id", "status"):
        op.create_index(op.f(f"ix_queue_attempts_{column}"), "queue_attempts", [column])


def downgrade() -> None:
    op.drop_table("queue_attempts")
    for column in ("attempts", "last_error", "current_payload_json"):
        op.drop_column("dead_letter_queue_items", column)
    op.drop_index("ix_integration_queue_lock", table_name="integration_queue_messages")
    op.drop_index("ix_integration_queue_business_key", table_name="integration_queue_messages")
    for name in ("finished_at", "started_at", "locked_until", "last_external_error_message", "last_error_message", "last_error_code", "original_payload_json", "locked_by", "connector_name", "target_system", "source_system", "business_key", "route_id", "endpoint_id", "flow_id", "run_id"):
        try:
            op.drop_index(op.f(f"ix_integration_queue_messages_{name}"), table_name="integration_queue_messages")
        except Exception:
            pass
        op.drop_column("integration_queue_messages", name)
    op.drop_column("integration_endpoints", "processing_mode")
