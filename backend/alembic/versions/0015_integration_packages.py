"""integration packages foundation

Revision ID: 0015_integration_packages
Revises: 0014_flow_builder_runtime
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_integration_packages"
down_revision: str | None = "0014_flow_builder_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "installed_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("official", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("manifest_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("install_log_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_installed_packages_package_id"), "installed_packages", ["package_id"], unique=True)
    op.create_index(op.f("ix_installed_packages_status"), "installed_packages", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_installed_packages_status"), table_name="installed_packages")
    op.drop_index(op.f("ix_installed_packages_package_id"), table_name="installed_packages")
    op.drop_table("installed_packages")
