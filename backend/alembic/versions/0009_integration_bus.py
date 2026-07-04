"""integration bus

Revision ID: 0009_integration_bus
Revises: 0008_onec_workbench
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_integration_bus"
down_revision: str | None = "0008_onec_workbench"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("operation_templates", sa.Column("operation_code", sa.String(length=180), nullable=True))
    op.add_column("operation_templates", sa.Column("direction", sa.String(length=40), server_default="outbound", nullable=False))
    op.add_column("operation_templates", sa.Column("input_mode", sa.String(length=40), nullable=True))
    op.add_column("operation_templates", sa.Column("output_mode", sa.String(length=40), nullable=True))
    op.add_column("operation_templates", sa.Column("target_connector_type", sa.String(length=100), nullable=True))
    op.add_column("operation_templates", sa.Column("default_body_mode", sa.String(length=40), nullable=True))
    op.add_column("operation_templates", sa.Column("default_content_type", sa.String(length=120), nullable=True))
    op.add_column("operation_templates", sa.Column("request_schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("operation_templates", sa.Column("example_request_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("operation_templates", sa.Column("example_response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index(op.f("ix_operation_templates_operation_code"), "operation_templates", ["operation_code"], unique=True)

    op.create_table(
        "integration_routes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("source_system", sa.String(length=255), nullable=True),
        sa.Column("target_system", sa.String(length=255), nullable=True),
        sa.Column("event_type", sa.String(length=255), nullable=True),
        sa.Column("message_type", sa.String(length=120), nullable=True),
        sa.Column("document_type", sa.String(length=120), nullable=True),
        sa.Column("operation", sa.String(length=160), nullable=True),
        sa.Column("condition_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=True),
        sa.Column("mapping_id", sa.Uuid(), nullable=True),
        sa.Column("target_connector_id", sa.Uuid(), nullable=True),
        sa.Column("operation_template_id", sa.Uuid(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["mapping_id"], ["mapping_definitions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["operation_template_id"], ["operation_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_connector_id"], ["connector_instances.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    for column in ["event_type", "message_type", "name", "operation", "priority", "source_system", "target_system"]:
        op.create_index(op.f(f"ix_integration_routes_{column}"), "integration_routes", [column], unique=column == "name")

    op.create_table(
        "integration_endpoints",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("input_mode", sa.String(length=40), nullable=False),
        sa.Column("response_mode", sa.String(length=40), nullable=False),
        sa.Column("default_source_system", sa.String(length=255), nullable=True),
        sa.Column("default_target_system", sa.String(length=255), nullable=True),
        sa.Column("default_event_type", sa.String(length=255), nullable=False),
        sa.Column("default_entity_type", sa.String(length=255), nullable=True),
        sa.Column("workflow_id", sa.Uuid(), nullable=True),
        sa.Column("route_id", sa.Uuid(), nullable=True),
        sa.Column("operation_template_id", sa.Uuid(), nullable=True),
        sa.Column("auth_mode", sa.String(length=40), nullable=False),
        sa.Column("auth_config_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["operation_template_id"], ["operation_templates.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["route_id"], ["integration_routes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(op.f("ix_integration_endpoints_name"), "integration_endpoints", ["name"], unique=True)
    op.create_index(op.f("ix_integration_endpoints_slug"), "integration_endpoints", ["slug"], unique=True)

    op.create_table(
        "odata_lookup_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("connector_id", sa.Uuid(), nullable=False),
        sa.Column("resource", sa.String(length=255), nullable=False),
        sa.Column("filter_template", sa.Text(), nullable=False),
        sa.Column("input_schema_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("extract_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("cache_ttl_seconds", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["connector_instances.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_odata_lookup_templates_connector_id"), "odata_lookup_templates", ["connector_id"], unique=False)
    op.create_index(op.f("ix_odata_lookup_templates_name"), "odata_lookup_templates", ["name"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_odata_lookup_templates_name"), table_name="odata_lookup_templates")
    op.drop_index(op.f("ix_odata_lookup_templates_connector_id"), table_name="odata_lookup_templates")
    op.drop_table("odata_lookup_templates")
    op.drop_index(op.f("ix_integration_endpoints_slug"), table_name="integration_endpoints")
    op.drop_index(op.f("ix_integration_endpoints_name"), table_name="integration_endpoints")
    op.drop_table("integration_endpoints")
    for column in ["target_system", "source_system", "priority", "operation", "name", "message_type", "event_type"]:
        op.drop_index(op.f(f"ix_integration_routes_{column}"), table_name="integration_routes")
    op.drop_table("integration_routes")
    op.drop_index(op.f("ix_operation_templates_operation_code"), table_name="operation_templates")
    for column in ["example_response_json", "example_request_json", "request_schema_json", "default_content_type", "default_body_mode", "target_connector_type", "output_mode", "input_mode", "direction", "operation_code"]:
        op.drop_column("operation_templates", column)
