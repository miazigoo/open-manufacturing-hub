"""visual flow builder runtime columns

Revision ID: 0014_flow_builder_runtime
Revises: 0013_integration_flows
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_flow_builder_runtime"
down_revision: str | None = "0013_integration_flows"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("integration_flows", sa.Column("compiled_workflow_id", sa.Uuid(), nullable=True))
    op.add_column("integration_flows", sa.Column("builder_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("integration_flows", sa.Column("last_validation_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("integration_flows", sa.Column("compiled_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key("fk_integration_flows_compiled_workflow_id_workflows", "integration_flows", "workflows", ["compiled_workflow_id"], ["id"], ondelete="SET NULL")
    op.create_index(op.f("ix_integration_flows_compiled_workflow_id"), "integration_flows", ["compiled_workflow_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_integration_flows_compiled_workflow_id"), table_name="integration_flows")
    op.drop_constraint("fk_integration_flows_compiled_workflow_id_workflows", "integration_flows", type_="foreignkey")
    op.drop_column("integration_flows", "compiled_at")
    op.drop_column("integration_flows", "last_validation_json")
    op.drop_column("integration_flows", "builder_json")
    op.drop_column("integration_flows", "compiled_workflow_id")
