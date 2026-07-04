"""saved test cases

Revision ID: 0011_saved_test_cases
Revises: 0010_external_errors
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_saved_test_cases"
down_revision: str | None = "0010_external_errors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saved_test_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("endpoint_id", sa.Uuid(), nullable=True),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("headers_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("body_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("input_mode", sa.String(length=40), nullable=False),
        sa.Column("expected_status", sa.String(length=80), nullable=True),
        sa.Column("last_run_event_id", sa.Uuid(), nullable=True),
        sa.Column("last_run_status", sa.String(length=80), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["endpoint_id"], ["integration_endpoints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["last_run_event_id"], ["integration_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_saved_test_cases_endpoint_id"), "saved_test_cases", ["endpoint_id"], unique=False)
    op.create_index(op.f("ix_saved_test_cases_name"), "saved_test_cases", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_saved_test_cases_name"), table_name="saved_test_cases")
    op.drop_index(op.f("ix_saved_test_cases_endpoint_id"), table_name="saved_test_cases")
    op.drop_table("saved_test_cases")
