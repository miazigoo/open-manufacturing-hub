"""marking code pool routing rules

Revision ID: 0035_pool_routing_rules
Revises: 0034_chz_agg_reg
Create Date: 2026-08-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0035_pool_routing_rules"
down_revision: str | None = "0034_chz_agg_reg"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "marking_code_pool_routing_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("match_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("targets_json", json_type(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_marking_code_pool_routing_rules_enabled"), "marking_code_pool_routing_rules", ["enabled"])
    op.create_index(op.f("ix_marking_code_pool_routing_rules_priority"), "marking_code_pool_routing_rules", ["priority"])


def downgrade() -> None:
    op.drop_index(op.f("ix_marking_code_pool_routing_rules_priority"), table_name="marking_code_pool_routing_rules")
    op.drop_index(op.f("ix_marking_code_pool_routing_rules_enabled"), table_name="marking_code_pool_routing_rules")
    op.drop_table("marking_code_pool_routing_rules")
