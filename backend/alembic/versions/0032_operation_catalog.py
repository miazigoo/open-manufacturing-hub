"""operation catalog reusable operations

Revision ID: 0032_operation_catalog
Revises: 0031_poll_odata_send_target
Create Date: 2026-07-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0032_operation_catalog"
down_revision: str | None = "0031_poll_odata_send_target"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "operation_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=180), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("connection_profile_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("method", sa.String(length=16), nullable=True),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("full_url", sa.Text(), nullable=True),
        sa.Column("headers_json", json_type(), nullable=True),
        sa.Column("body_type", sa.String(length=40), nullable=True),
        sa.Column("request_template_json", json_type(), nullable=True),
        sa.Column("request_template_text", sa.Text(), nullable=True),
        sa.Column("response_body_type", sa.String(length=40), nullable=True),
        sa.Column("success_condition_json", json_type(), nullable=True),
        sa.Column("response_extractors_json", json_type(), nullable=True),
        sa.Column("sample_request_json", json_type(), nullable=True),
        sa.Column("sample_response_json", json_type(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=True),
        sa.Column("tags_json", json_type(), nullable=True),
        sa.Column("package_id", sa.String(length=160), nullable=True),
        sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_test_success", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connection_profile_id"], ["connector_instances.id"], name="fk_operation_profiles_connection_profile_id", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_operation_profiles_name"), "operation_profiles", ["name"], unique=False)
    op.create_index(op.f("ix_operation_profiles_code"), "operation_profiles", ["code"], unique=True)
    op.create_index(op.f("ix_operation_profiles_kind"), "operation_profiles", ["kind"], unique=False)
    op.create_index(op.f("ix_operation_profiles_connection_profile_id"), "operation_profiles", ["connection_profile_id"], unique=False)
    op.create_index(op.f("ix_operation_profiles_enabled"), "operation_profiles", ["enabled"], unique=False)
    op.create_index(op.f("ix_operation_profiles_package_id"), "operation_profiles", ["package_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_operation_profiles_package_id"), table_name="operation_profiles")
    op.drop_index(op.f("ix_operation_profiles_enabled"), table_name="operation_profiles")
    op.drop_index(op.f("ix_operation_profiles_connection_profile_id"), table_name="operation_profiles")
    op.drop_index(op.f("ix_operation_profiles_kind"), table_name="operation_profiles")
    op.drop_index(op.f("ix_operation_profiles_code"), table_name="operation_profiles")
    op.drop_index(op.f("ix_operation_profiles_name"), table_name="operation_profiles")
    op.drop_table("operation_profiles")
