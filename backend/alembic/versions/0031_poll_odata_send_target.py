"""poll odata send target pattern

Revision ID: 0031_poll_odata_send_target
Revises: 0030_marking_code_pool_exports
Create Date: 2026-07-12
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0031_poll_odata_send_target"
down_revision: str | None = "0030_marking_code_pool_exports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.add_column("polling_jobs", sa.Column("slug", sa.String(length=160), nullable=True))
    op.add_column("polling_jobs", sa.Column("integration_flow_id", sa.Uuid(), nullable=True))
    op.add_column("polling_jobs", sa.Column("config_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("polling_jobs", sa.Column("cursor_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("polling_jobs", sa.Column("schedule_type", sa.String(length=40), nullable=False, server_default="interval_minutes"))
    op.create_index(op.f("ix_polling_jobs_slug"), "polling_jobs", ["slug"], unique=True)
    op.create_index(op.f("ix_polling_jobs_integration_flow_id"), "polling_jobs", ["integration_flow_id"])
    op.create_foreign_key("fk_polling_jobs_integration_flow_id", "polling_jobs", "integration_flows", ["integration_flow_id"], ["id"], ondelete="SET NULL")

    op.add_column("polling_job_runs", sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("polling_job_runs", sa.Column("event_id", sa.Uuid(), nullable=True))
    op.add_column("polling_job_runs", sa.Column("cursor_before_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("polling_job_runs", sa.Column("cursor_after_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.create_foreign_key("fk_polling_job_runs_event_id", "polling_job_runs", "integration_events", ["event_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_polling_job_runs_event_id", "polling_job_runs", type_="foreignkey")
    op.drop_column("polling_job_runs", "cursor_after_json")
    op.drop_column("polling_job_runs", "cursor_before_json")
    op.drop_column("polling_job_runs", "event_id")
    op.drop_column("polling_job_runs", "sent_count")

    op.drop_constraint("fk_polling_jobs_integration_flow_id", "polling_jobs", type_="foreignkey")
    op.drop_index(op.f("ix_polling_jobs_integration_flow_id"), table_name="polling_jobs")
    op.drop_index(op.f("ix_polling_jobs_slug"), table_name="polling_jobs")
    op.drop_column("polling_jobs", "schedule_type")
    op.drop_column("polling_jobs", "cursor_json")
    op.drop_column("polling_jobs", "config_json")
    op.drop_column("polling_jobs", "integration_flow_id")
    op.drop_column("polling_jobs", "slug")
