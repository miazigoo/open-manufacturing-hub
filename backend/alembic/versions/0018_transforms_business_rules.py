"""transforms and business rule sets

Revision ID: 0018_transforms_business_rules
Revises: 0017_business_objects_resolvers
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_transforms_business_rules"
down_revision: str | None = "0017_business_objects_resolvers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "business_rule_sets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("scope", sa.String(length=80), nullable=True),
        sa.Column("rules_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_business_rule_sets_name"),
    )
    for column in ("name", "enabled", "scope"):
        op.create_index(op.f(f"ix_business_rule_sets_{column}"), "business_rule_sets", [column])
    op.create_index("ix_business_rule_sets_scope_enabled", "business_rule_sets", ["scope", "enabled"])


def downgrade() -> None:
    op.drop_table("business_rule_sets")
