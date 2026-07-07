"""integration master input contract drafts

Revision ID: 0027_integration_master_drafts
Revises: 0026_env_profiles_changes
Create Date: 2026-07-07
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027_integration_master_drafts"
down_revision: str | None = "0026_env_profiles_changes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def jsonb_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "integration_master_drafts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("scenario_key", sa.String(length=160), nullable=True),
        sa.Column("input_mode", sa.String(length=40), nullable=False),
        sa.Column("source_system", sa.String(length=80), nullable=False),
        sa.Column("contract_json", jsonb_type(), nullable=False),
        sa.Column("parse_result_json", jsonb_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_integration_master_drafts_name"), "integration_master_drafts", ["name"], unique=False)
    op.create_index(op.f("ix_integration_master_drafts_slug"), "integration_master_drafts", ["slug"], unique=False)
    op.create_index(op.f("ix_integration_master_drafts_scenario_key"), "integration_master_drafts", ["scenario_key"], unique=False)
    op.create_index(op.f("ix_integration_master_drafts_input_mode"), "integration_master_drafts", ["input_mode"], unique=False)
    op.create_index(op.f("ix_integration_master_drafts_source_system"), "integration_master_drafts", ["source_system"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_integration_master_drafts_source_system"), table_name="integration_master_drafts")
    op.drop_index(op.f("ix_integration_master_drafts_input_mode"), table_name="integration_master_drafts")
    op.drop_index(op.f("ix_integration_master_drafts_scenario_key"), table_name="integration_master_drafts")
    op.drop_index(op.f("ix_integration_master_drafts_slug"), table_name="integration_master_drafts")
    op.drop_index(op.f("ix_integration_master_drafts_name"), table_name="integration_master_drafts")
    op.drop_table("integration_master_drafts")
