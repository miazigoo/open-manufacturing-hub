"""core skeleton

Revision ID: 0001_core_skeleton
Revises:
Create Date: 2026-07-02
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_core_skeleton"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("source_system", sa.String(length=255), nullable=False),
        sa.Column("target_system", sa.String(length=255), nullable=True),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=255), nullable=True),
        sa.Column("entity_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.Enum("new", "processing", "success", "failed", "retry_waiting", "cancelled", "expired", native_enum=False), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_integration_events_correlation_id"), "integration_events", ["correlation_id"], unique=False)

    op.create_table(
        "event_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("run_number", sa.Integer(), nullable=False),
        sa.Column("mode", sa.Enum("normal", "replay", "replay_from_step", "edit_replay", "dry_run", native_enum=False), nullable=False),
        sa.Column("status", sa.Enum("created", "running", "success", "failed", "cancelled", "dry_run_success", "dry_run_failed", native_enum=False), nullable=False),
        sa.Column("parent_run_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["integration_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_run_id"], ["event_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_runs_event_run_number", "event_runs", ["event_id", "run_number"], unique=True)
    op.create_index(op.f("ix_event_runs_event_id"), "event_runs", ["event_id"], unique=False)

    op.create_table(
        "event_steps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.Enum("pending", "running", "success", "failed", "skipped", "dry_run", native_enum=False), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["event_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_event_steps_run_step_order", "event_steps", ["run_id", "step_order"], unique=True)
    op.create_index(op.f("ix_event_steps_run_id"), "event_steps", ["run_id"], unique=False)

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("step_id", sa.Uuid(), nullable=True),
        sa.Column("artifact_type", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["integration_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["event_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["event_steps.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_artifacts_event_id"), "artifacts", ["event_id"], unique=False)
    op.create_index(op.f("ix_artifacts_run_id"), "artifacts", ["run_id"], unique=False)
    op.create_index(op.f("ix_artifacts_step_id"), "artifacts", ["step_id"], unique=False)

    op.create_table(
        "incidents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint"),
    )


def downgrade() -> None:
    op.drop_table("incidents")
    op.drop_index(op.f("ix_artifacts_step_id"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_run_id"), table_name="artifacts")
    op.drop_index(op.f("ix_artifacts_event_id"), table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index(op.f("ix_event_steps_run_id"), table_name="event_steps")
    op.drop_index("ix_event_steps_run_step_order", table_name="event_steps")
    op.drop_table("event_steps")
    op.drop_index(op.f("ix_event_runs_event_id"), table_name="event_runs")
    op.drop_index("ix_event_runs_event_run_number", table_name="event_runs")
    op.drop_table("event_runs")
    op.drop_index(op.f("ix_integration_events_correlation_id"), table_name="integration_events")
    op.drop_table("integration_events")
