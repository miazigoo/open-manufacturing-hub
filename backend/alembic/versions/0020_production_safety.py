"""production safety layer

Revision ID: 0020_production_safety
Revises: 0019_optional_auth_package
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_production_safety"
down_revision: str | None = "0019_optional_auth_package"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "backup_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("backup_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_backup_records_backup_type"), "backup_records", ["backup_type"], unique=False)
    op.create_index(op.f("ix_backup_records_status"), "backup_records", ["status"], unique=False)
    op.create_table(
        "production_state",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("update_mode_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("update_mode_message", sa.Text(), nullable=True),
        sa.Column("update_mode_enabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("update_mode_enabled_by", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("production_state")
    op.drop_index(op.f("ix_backup_records_status"), table_name="backup_records")
    op.drop_index(op.f("ix_backup_records_backup_type"), table_name="backup_records")
    op.drop_table("backup_records")
