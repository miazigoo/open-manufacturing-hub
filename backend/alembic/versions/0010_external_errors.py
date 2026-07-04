"""external errors

Revision ID: 0010_external_errors
Revises: 0009_integration_bus
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_external_errors"
down_revision: str | None = "0009_integration_bus"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "external_error_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("step_id", sa.Uuid(), nullable=True),
        sa.Column("incident_id", sa.Uuid(), nullable=True),
        sa.Column("source_system", sa.String(length=255), nullable=True),
        sa.Column("target_system", sa.String(length=255), nullable=True),
        sa.Column("connector_type", sa.String(length=100), nullable=True),
        sa.Column("connector_name", sa.String(length=255), nullable=True),
        sa.Column("operation", sa.String(length=255), nullable=True),
        sa.Column("endpoint_url", sa.Text(), nullable=True),
        sa.Column("http_method", sa.String(length=16), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("normalized_code", sa.String(length=255), nullable=False),
        sa.Column("normalized_message", sa.Text(), nullable=False),
        sa.Column("human_title", sa.String(length=255), nullable=True),
        sa.Column("human_summary", sa.Text(), nullable=True),
        sa.Column("developer_message", sa.Text(), nullable=True),
        sa.Column("hint", sa.Text(), nullable=True),
        sa.Column("external_error_code", sa.String(length=255), nullable=True),
        sa.Column("external_error_message", sa.Text(), nullable=True),
        sa.Column("external_error_type", sa.String(length=120), nullable=True),
        sa.Column("response_content_type", sa.String(length=255), nullable=True),
        sa.Column("response_body_text", sa.Text(), nullable=True),
        sa.Column("response_body_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_body_xml", sa.Text(), nullable=True),
        sa.Column("response_body_preview", sa.Text(), nullable=True),
        sa.Column("response_body_sha256", sa.String(length=64), nullable=True),
        sa.Column("response_size_bytes", sa.Integer(), nullable=True),
        sa.Column("request_artifact_id", sa.Uuid(), nullable=True),
        sa.Column("response_artifact_id", sa.Uuid(), nullable=True),
        sa.Column("error_artifact_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["error_artifact_id"], ["artifacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["event_id"], ["integration_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["request_artifact_id"], ["artifacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["response_artifact_id"], ["artifacts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["event_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["step_id"], ["event_steps.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["event_id", "incident_id", "run_id", "step_id"]:
        op.create_index(op.f(f"ix_external_error_records_{column}"), "external_error_records", [column], unique=False)
    op.create_index("ix_external_error_records_event_created", "external_error_records", ["event_id", "created_at"], unique=False)
    op.create_index("ix_external_error_records_incident_created", "external_error_records", ["incident_id", "created_at"], unique=False)
    op.create_index("ix_external_error_records_step", "external_error_records", ["step_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_external_error_records_step", table_name="external_error_records")
    op.drop_index("ix_external_error_records_incident_created", table_name="external_error_records")
    op.drop_index("ix_external_error_records_event_created", table_name="external_error_records")
    for column in ["step_id", "run_id", "incident_id", "event_id"]:
        op.drop_index(op.f(f"ix_external_error_records_{column}"), table_name="external_error_records")
    op.drop_table("external_error_records")
