"""execution engine step metadata

Revision ID: 0005_execution_engine
Revises: 0004_workflows_mappings
Create Date: 2026-07-02
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_execution_engine"
down_revision: str | None = "0004_workflows_mappings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("workflows", "event_type", existing_type=sa.String(length=255), nullable=True)
    op.add_column("event_steps", sa.Column("step_config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("event_steps", sa.Column("condition", sa.String(length=50), nullable=True))
    op.alter_column("event_steps", "step_config_json", server_default=None)


def downgrade() -> None:
    op.drop_column("event_steps", "condition")
    op.drop_column("event_steps", "step_config_json")
    op.alter_column("workflows", "event_type", existing_type=sa.String(length=255), nullable=False)
