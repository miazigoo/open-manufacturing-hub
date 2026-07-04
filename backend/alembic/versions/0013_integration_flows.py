"""integration flows and no-code matchers

Revision ID: 0013_integration_flows
Revises: 0012_enterprise_runtime
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_integration_flows"
down_revision: str | None = "0012_enterprise_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "integration_flows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("target_type", sa.String(length=40), nullable=False),
        sa.Column("endpoint_id", sa.Uuid(), nullable=True),
        sa.Column("route_id", sa.Uuid(), nullable=True),
        sa.Column("workflow_id", sa.Uuid(), nullable=True),
        sa.Column("mapping_id", sa.Uuid(), nullable=True),
        sa.Column("target_connector_id", sa.Uuid(), nullable=True),
        sa.Column("operation_template_id", sa.Uuid(), nullable=True),
        sa.Column("matcher_group_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("action_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("test_payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("test_payload_text", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["endpoint_id"], ["integration_endpoints.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mapping_id"], ["mapping_definitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["operation_template_id"], ["operation_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["route_id"], ["integration_routes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_connector_id"], ["connector_instances.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("name", "slug", "source_type", "target_type", "endpoint_id", "route_id", "workflow_id", "mapping_id", "target_connector_id", "operation_template_id"):
        op.create_index(op.f(f"ix_integration_flows_{column}"), "integration_flows", [column], unique=column in {"name", "slug"})


def downgrade() -> None:
    op.drop_table("integration_flows")
