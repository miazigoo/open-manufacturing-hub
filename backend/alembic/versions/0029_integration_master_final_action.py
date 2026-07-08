"""integration master final action drafts

Revision ID: 0029_im_final_action
Revises: 0028_im_odata_steps
Create Date: 2026-07-08
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0029_im_final_action"
down_revision: str | None = "0028_im_odata_steps"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def jsonb_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.add_column("integration_master_drafts", sa.Column("final_action_json", jsonb_type(), nullable=True))


def downgrade() -> None:
    op.drop_column("integration_master_drafts", "final_action_json")
