"""package runtime capabilities

Revision ID: 0023_package_capabilities
Revises: 0022_secrets_store
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023_package_capabilities"
down_revision: str | None = "0022_secrets_store"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def jsonb_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "package_runtime_capabilities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.String(length=160), nullable=False),
        sa.Column("capability_type", sa.String(length=80), nullable=False),
        sa.Column("capability_code", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", jsonb_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("package_id", "capability_type", "capability_code", name="uq_package_runtime_capability"),
    )
    op.create_index(op.f("ix_package_runtime_capabilities_package_id"), "package_runtime_capabilities", ["package_id"], unique=False)
    op.create_index(op.f("ix_package_runtime_capabilities_capability_type"), "package_runtime_capabilities", ["capability_type"], unique=False)
    op.create_index(op.f("ix_package_runtime_capabilities_capability_code"), "package_runtime_capabilities", ["capability_code"], unique=False)
    op.create_index(op.f("ix_package_runtime_capabilities_enabled"), "package_runtime_capabilities", ["enabled"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_package_runtime_capabilities_enabled"), table_name="package_runtime_capabilities")
    op.drop_index(op.f("ix_package_runtime_capabilities_capability_code"), table_name="package_runtime_capabilities")
    op.drop_index(op.f("ix_package_runtime_capabilities_capability_type"), table_name="package_runtime_capabilities")
    op.drop_index(op.f("ix_package_runtime_capabilities_package_id"), table_name="package_runtime_capabilities")
    op.drop_table("package_runtime_capabilities")
