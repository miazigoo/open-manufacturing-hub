"""health checks latest index

Revision ID: 0036_health_checks_idx
Revises: 0035_pool_routing_rules
Create Date: 2026-08-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_health_checks_idx"
down_revision: str | None = "0035_pool_routing_rules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_health_checks_latest",
        "health_checks",
        ["component_type", "component_name", "site_id", sa.text("checked_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_health_checks_latest", table_name="health_checks")
