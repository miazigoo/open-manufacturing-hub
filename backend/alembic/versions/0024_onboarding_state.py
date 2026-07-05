"""guided onboarding state

Revision ID: 0024_onboarding_state
Revises: 0023_package_capabilities
Create Date: 2026-07-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024_onboarding_state"
down_revision: str | None = "0023_package_capabilities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def jsonb_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "onboarding_state",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skipped", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("skipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", jsonb_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_onboarding_state_key"), "onboarding_state", ["key"], unique=True)
    op.create_index(op.f("ix_onboarding_state_completed"), "onboarding_state", ["completed"], unique=False)
    op.create_index(op.f("ix_onboarding_state_skipped"), "onboarding_state", ["skipped"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_onboarding_state_skipped"), table_name="onboarding_state")
    op.drop_index(op.f("ix_onboarding_state_completed"), table_name="onboarding_state")
    op.drop_index(op.f("ix_onboarding_state_key"), table_name="onboarding_state")
    op.drop_table("onboarding_state")
