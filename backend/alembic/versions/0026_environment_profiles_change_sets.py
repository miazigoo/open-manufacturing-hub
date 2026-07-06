"""environment profiles and change sets

Revision ID: 0026_env_profiles_changes
Revises: 0025_config_versions
Create Date: 2026-07-05
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026_env_profiles_changes"
down_revision: str | None = "0025_config_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def jsonb_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "environments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("environment_type", sa.Enum("development", "test", "staging", "production", "custom", name="environmenttype", native_enum=False), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_environments_code"),
        sa.UniqueConstraint("name", name="uq_environments_name"),
    )
    op.create_index("ix_environments_code", "environments", ["code"], unique=False)
    op.create_index("ix_environments_current", "environments", ["is_current"], unique=False)
    op.create_index("ix_environments_environment_type", "environments", ["environment_type"], unique=False)
    op.create_index("ix_environments_name", "environments", ["name"], unique=False)

    op.create_table(
        "environment_variables",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("environment_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("value_json", jsonb_type(), nullable=True),
        sa.Column("secret_ref", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["environment_id"], ["environments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("environment_id", "key", name="uq_environment_variables_environment_key"),
    )
    op.create_index("ix_environment_variables_environment_id", "environment_variables", ["environment_id"], unique=False)
    op.create_index("ix_environment_variables_key", "environment_variables", ["key"], unique=False)

    op.create_table(
        "change_sets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_environment", sa.String(length=160), nullable=True),
        sa.Column("target_environment", sa.String(length=160), nullable=True),
        sa.Column("status", sa.Enum("draft", "exported", "import_previewed", "applied", "failed", "rolled_back", name="changesetstatus", native_enum=False), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", jsonb_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_change_sets_created_at", "change_sets", ["created_at"], unique=False)
    op.create_index("ix_change_sets_source_environment", "change_sets", ["source_environment"], unique=False)
    op.create_index("ix_change_sets_status", "change_sets", ["status"], unique=False)
    op.create_index("ix_change_sets_target_environment", "change_sets", ["target_environment"], unique=False)

    op.create_table(
        "change_set_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("change_set_id", sa.Uuid(), nullable=False),
        sa.Column("object_type", sa.String(length=80), nullable=False),
        sa.Column("object_id", sa.String(length=80), nullable=True),
        sa.Column("object_name", sa.String(length=255), nullable=True),
        sa.Column("operation", sa.Enum("create", "update", "enable", "disable", "delete_disabled_in_mvp", name="changesetoperation", native_enum=False), nullable=False),
        sa.Column("config_json", jsonb_type(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=True),
        sa.Column("package_id", sa.String(length=160), nullable=True),
        sa.Column("dependencies_json", jsonb_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["change_set_id"], ["change_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["version_id"], ["config_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_change_set_items_change_set", "change_set_items", ["change_set_id"], unique=False)
    op.create_index("ix_change_set_items_object", "change_set_items", ["object_type", "object_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_change_set_items_object", table_name="change_set_items")
    op.drop_index("ix_change_set_items_change_set", table_name="change_set_items")
    op.drop_table("change_set_items")
    op.drop_index("ix_change_sets_target_environment", table_name="change_sets")
    op.drop_index("ix_change_sets_status", table_name="change_sets")
    op.drop_index("ix_change_sets_source_environment", table_name="change_sets")
    op.drop_index("ix_change_sets_created_at", table_name="change_sets")
    op.drop_table("change_sets")
    op.drop_index("ix_environment_variables_key", table_name="environment_variables")
    op.drop_index("ix_environment_variables_environment_id", table_name="environment_variables")
    op.drop_table("environment_variables")
    op.drop_index("ix_environments_name", table_name="environments")
    op.drop_index("ix_environments_environment_type", table_name="environments")
    op.drop_index("ix_environments_current", table_name="environments")
    op.drop_index("ix_environments_code", table_name="environments")
    op.drop_table("environments")
