"""connector instances

Revision ID: 0003_connector_instances
Revises: 0002_operational_modules
Create Date: 2026-07-02
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_connector_instances"
down_revision: str | None = "0002_operational_modules"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "connector_instances",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("connector_type", sa.String(length=100), nullable=False),
        sa.Column("direction", sa.Enum("source", "target", "bidirectional", native_enum=False), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Enum("enabled", "disabled", "maintenance", "error", "unknown", native_enum=False), nullable=False),
        sa.Column("last_health_status", sa.Enum("ok", "warning", "down", "unknown", "maintenance", native_enum=False), nullable=True),
        sa.Column("last_health_message", sa.Text(), nullable=True),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_connector_instances_connector_type"), "connector_instances", ["connector_type"], unique=False)
    op.create_index(op.f("ix_connector_instances_name"), "connector_instances", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_connector_instances_name"), table_name="connector_instances")
    op.drop_index(op.f("ix_connector_instances_connector_type"), table_name="connector_instances")
    op.drop_table("connector_instances")
