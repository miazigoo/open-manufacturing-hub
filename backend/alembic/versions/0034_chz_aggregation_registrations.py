"""chz aggregation registrations

Revision ID: 0034_chz_aggregation_registrations
Revises: 0033_data_contract_mapping
Create Date: 2026-07-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0034_chz_aggregation_registrations"
down_revision: str | None = "0033_data_contract_mapping"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "chz_aggregation_registrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_system", sa.String(length=255), nullable=False),
        sa.Column("source_document_id", sa.String(length=255), nullable=True),
        sa.Column("source_file_name", sa.String(length=255), nullable=True),
        sa.Column("order_number_1c", sa.String(length=255), nullable=False),
        sa.Column("order_number_external", sa.String(length=255), nullable=True),
        sa.Column("total_codes", sa.Integer(), nullable=False),
        sa.Column("total_aggregates", sa.Integer(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("forwarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chz_aggregation_registrations_content_sha256"), "chz_aggregation_registrations", ["content_sha256"])
    op.create_index("ix_chz_aggregation_reg_order", "chz_aggregation_registrations", ["order_number_1c"])
    op.create_index(op.f("ix_chz_aggregation_registrations_order_number_1c"), "chz_aggregation_registrations", ["order_number_1c"])
    op.create_index("ix_chz_aggregation_reg_source", "chz_aggregation_registrations", ["source_system", "source_document_id"])
    op.create_index(op.f("ix_chz_aggregation_registrations_source_document_id"), "chz_aggregation_registrations", ["source_document_id"])
    op.create_index(op.f("ix_chz_aggregation_registrations_source_system"), "chz_aggregation_registrations", ["source_system"])
    op.create_index(op.f("ix_chz_aggregation_registrations_status"), "chz_aggregation_registrations", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_chz_aggregation_registrations_status"), table_name="chz_aggregation_registrations")
    op.drop_index(op.f("ix_chz_aggregation_registrations_source_system"), table_name="chz_aggregation_registrations")
    op.drop_index(op.f("ix_chz_aggregation_registrations_source_document_id"), table_name="chz_aggregation_registrations")
    op.drop_index("ix_chz_aggregation_reg_source", table_name="chz_aggregation_registrations")
    op.drop_index(op.f("ix_chz_aggregation_registrations_order_number_1c"), table_name="chz_aggregation_registrations")
    op.drop_index("ix_chz_aggregation_reg_order", table_name="chz_aggregation_registrations")
    op.drop_index(op.f("ix_chz_aggregation_registrations_content_sha256"), table_name="chz_aggregation_registrations")
    op.drop_table("chz_aggregation_registrations")
