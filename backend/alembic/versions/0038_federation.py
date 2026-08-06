"""federation sync runs

Revision ID: 0038_federation
Revises: 0037_data_inbox
Create Date: 2026-08-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0038_federation"
down_revision: str | None = "0037_data_inbox"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "federation_sync_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("direction", sa.String(length=40), nullable=False, server_default="pull"),
        sa.Column("center_url", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("version", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("details_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_federation_sync_runs_status"), "federation_sync_runs", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_federation_sync_runs_status"), table_name="federation_sync_runs")
    op.drop_table("federation_sync_runs")
