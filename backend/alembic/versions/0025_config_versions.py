"""configuration versioning

Revision ID: 0025_config_versions
Revises: 0024_onboarding_state
Create Date: 2026-07-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025_config_versions"
down_revision: str | None = "0024_onboarding_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def jsonb_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "config_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("object_type", sa.String(length=80), nullable=False),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("object_name", sa.String(length=255), nullable=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("draft", "active", "archived", "rollback", "rejected", name="configversionstatus", native_enum=False), nullable=False),
        sa.Column("config_json", jsonb_type(), nullable=False),
        sa.Column("metadata_json", jsonb_type(), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("published_by", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rollback_of_version_id", sa.Uuid(), nullable=True),
        sa.Column("test_status", sa.Enum("not_tested", "passed", "failed", "warning", name="configversionteststatus", native_enum=False), nullable=False, server_default="not_tested"),
        sa.Column("last_test_event_id", sa.Uuid(), nullable=True),
        sa.Column("last_test_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["last_test_event_id"], ["integration_events.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rollback_of_version_id"], ["config_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_type", "object_id", "version_number", name="uq_config_versions_object_version"),
    )
    op.create_index("ix_config_versions_object", "config_versions", ["object_type", "object_id"], unique=False)
    op.create_index("ix_config_versions_status", "config_versions", ["status"], unique=False)
    op.create_index("uq_config_versions_effective_active", "config_versions", ["object_type", "object_id"], unique=True, postgresql_where=sa.text("status in ('active', 'rollback')"))


def downgrade() -> None:
    op.drop_index("uq_config_versions_effective_active", table_name="config_versions")
    op.drop_index("ix_config_versions_status", table_name="config_versions")
    op.drop_index("ix_config_versions_object", table_name="config_versions")
    op.drop_table("config_versions")
