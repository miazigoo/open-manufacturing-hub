"""integration master odata step drafts

Revision ID: 0028_integration_master_odata_steps
Revises: 0027_integration_master_drafts
Create Date: 2026-07-07
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028_integration_master_odata_steps"
down_revision: str | None = "0027_integration_master_drafts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def jsonb_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.add_column("integration_master_drafts", sa.Column("odata_steps_json", jsonb_type(), nullable=True))


def downgrade() -> None:
    op.drop_column("integration_master_drafts", "odata_steps_json")
