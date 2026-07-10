"""marking code pool exports

Revision ID: 0030_marking_code_pool_exports
Revises: 0029_im_final_action
Create Date: 2026-07-10
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030_marking_code_pool_exports"
down_revision: str | None = "0029_im_final_action"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "marking_code_pool_exports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_system", sa.String(length=255), nullable=False),
        sa.Column("source_document_id", sa.String(length=255), nullable=True),
        sa.Column("source_document_name", sa.String(length=255), nullable=True),
        sa.Column("order_number", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("total_codes", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("forwarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_marking_code_pool_exports_content_sha256"), "marking_code_pool_exports", ["content_sha256"])
    op.create_index(op.f("ix_marking_code_pool_exports_file_name"), "marking_code_pool_exports", ["file_name"])
    op.create_index(op.f("ix_marking_code_pool_exports_order_number"), "marking_code_pool_exports", ["order_number"])
    op.create_index("ix_marking_code_pool_exports_source_document", "marking_code_pool_exports", ["source_system", "source_document_id"])
    op.create_index(op.f("ix_marking_code_pool_exports_source_document_id"), "marking_code_pool_exports", ["source_document_id"])
    op.create_index(op.f("ix_marking_code_pool_exports_source_system"), "marking_code_pool_exports", ["source_system"])
    op.create_index(op.f("ix_marking_code_pool_exports_status"), "marking_code_pool_exports", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_marking_code_pool_exports_status"), table_name="marking_code_pool_exports")
    op.drop_index(op.f("ix_marking_code_pool_exports_source_system"), table_name="marking_code_pool_exports")
    op.drop_index(op.f("ix_marking_code_pool_exports_source_document_id"), table_name="marking_code_pool_exports")
    op.drop_index("ix_marking_code_pool_exports_source_document", table_name="marking_code_pool_exports")
    op.drop_index(op.f("ix_marking_code_pool_exports_order_number"), table_name="marking_code_pool_exports")
    op.drop_index(op.f("ix_marking_code_pool_exports_file_name"), table_name="marking_code_pool_exports")
    op.drop_index(op.f("ix_marking_code_pool_exports_content_sha256"), table_name="marking_code_pool_exports")
    op.drop_table("marking_code_pool_exports")
