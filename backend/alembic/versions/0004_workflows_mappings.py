"""workflows and mappings

Revision ID: 0004_workflows_mappings
Revises: 0003_connector_instances
Create Date: 2026-07-02
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_workflows_mappings"
down_revision: str | None = "0003_connector_instances"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mapping_definitions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_entity", sa.String(length=100), nullable=True),
        sa.Column("target_entity", sa.String(length=100), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_mapping_definitions_name"), "mapping_definitions", ["name"], unique=True)

    op.create_table(
        "mapping_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mapping_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("rules_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("target_schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["mapping_id"], ["mapping_definitions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mapping_versions_mapping_id"), "mapping_versions", ["mapping_id"], unique=False)
    op.create_index("ix_mapping_versions_mapping_version", "mapping_versions", ["mapping_id", "version"], unique=True)

    op.create_table(
        "workflows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("source_system", sa.String(length=255), nullable=True),
        sa.Column("target_system", sa.String(length=255), nullable=True),
        sa.Column("entity_type", sa.String(length=255), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("steps_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_mapping_version_id", sa.Uuid(), nullable=True),
        sa.Column("target_mapping_version_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["source_mapping_version_id"], ["mapping_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_mapping_version_id"], ["mapping_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_workflows_name"), "workflows", ["name"], unique=True)
    op.create_index(op.f("ix_workflows_event_type"), "workflows", ["event_type"], unique=False)
    op.create_index(op.f("ix_workflows_source_system"), "workflows", ["source_system"], unique=False)
    op.create_index(op.f("ix_workflows_target_system"), "workflows", ["target_system"], unique=False)
    op.create_index("ix_workflows_trigger", "workflows", ["event_type", "source_system", "target_system", "enabled"], unique=False)

    op.add_column("event_runs", sa.Column("workflow_id", sa.Uuid(), nullable=True))
    op.add_column("event_runs", sa.Column("workflow_name", sa.String(length=255), nullable=True))
    op.add_column("event_runs", sa.Column("workflow_version", sa.Integer(), nullable=True))
    op.add_column("event_runs", sa.Column("mapping_versions_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.create_foreign_key("fk_event_runs_workflow_id", "event_runs", "workflows", ["workflow_id"], ["id"], ondelete="SET NULL")
    op.alter_column("event_runs", "mapping_versions_json", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_event_runs_workflow_id", "event_runs", type_="foreignkey")
    op.drop_column("event_runs", "mapping_versions_json")
    op.drop_column("event_runs", "workflow_version")
    op.drop_column("event_runs", "workflow_name")
    op.drop_column("event_runs", "workflow_id")

    op.drop_index("ix_workflows_trigger", table_name="workflows")
    op.drop_index(op.f("ix_workflows_target_system"), table_name="workflows")
    op.drop_index(op.f("ix_workflows_source_system"), table_name="workflows")
    op.drop_index(op.f("ix_workflows_event_type"), table_name="workflows")
    op.drop_index(op.f("ix_workflows_name"), table_name="workflows")
    op.drop_table("workflows")

    op.drop_index("ix_mapping_versions_mapping_version", table_name="mapping_versions")
    op.drop_index(op.f("ix_mapping_versions_mapping_id"), table_name="mapping_versions")
    op.drop_table("mapping_versions")

    op.drop_index(op.f("ix_mapping_definitions_name"), table_name="mapping_definitions")
    op.drop_table("mapping_definitions")
