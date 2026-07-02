"""1C polling jobs

Revision ID: 0006_onec_polling
Revises: 0005_execution_engine
Create Date: 2026-07-02
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_onec_polling"
down_revision: str | None = "0005_execution_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "polling_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("source_connector_id", sa.Uuid(), nullable=False),
        sa.Column("target_system", sa.String(length=255), nullable=True),
        sa.Column("resource", sa.String(length=255), nullable=False),
        sa.Column("query_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=255), nullable=True),
        sa.Column("entity_id_field", sa.String(length=255), nullable=True),
        sa.Column("correlation_id_field", sa.String(length=255), nullable=True),
        sa.Column("updated_at_field", sa.String(length=255), nullable=True),
        sa.Column("cursor_value", sa.String(length=1024), nullable=True),
        sa.Column("cursor_type", sa.Enum("none", "updated_at", "skip", "custom", native_enum=False), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("idle", "running", "success", "failed", "disabled", native_enum=False), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_connector_id"], ["connector_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_polling_jobs_name"), "polling_jobs", ["name"], unique=True)
    op.create_index(op.f("ix_polling_jobs_source_connector_id"), "polling_jobs", ["source_connector_id"], unique=False)

    op.create_table(
        "source_event_cursors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_connector_id", sa.Uuid(), nullable=False),
        sa.Column("source_resource", sa.String(length=255), nullable=False),
        sa.Column("source_entity_id", sa.String(length=512), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("last_seen_hash", sa.String(length=64), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_event_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_event_id"], ["integration_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_connector_id"], ["connector_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_source_event_cursors_source_connector_id"), "source_event_cursors", ["source_connector_id"], unique=False)
    op.create_index("ix_source_event_cursor_unique", "source_event_cursors", ["source_connector_id", "source_resource", "source_entity_id", "event_type"], unique=True)

    op.create_table(
        "polling_job_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Enum("idle", "running", "success", "failed", "disabled", native_enum=False), nullable=False),
        sa.Column("items_read", sa.Integer(), nullable=False),
        sa.Column("events_created", sa.Integer(), nullable=False),
        sa.Column("items_skipped", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["polling_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_polling_job_runs_job_id"), "polling_job_runs", ["job_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_polling_job_runs_job_id"), table_name="polling_job_runs")
    op.drop_table("polling_job_runs")
    op.drop_index("ix_source_event_cursor_unique", table_name="source_event_cursors")
    op.drop_index(op.f("ix_source_event_cursors_source_connector_id"), table_name="source_event_cursors")
    op.drop_table("source_event_cursors")
    op.drop_index(op.f("ix_polling_jobs_source_connector_id"), table_name="polling_jobs")
    op.drop_index(op.f("ix_polling_jobs_name"), table_name="polling_jobs")
    op.drop_table("polling_jobs")
