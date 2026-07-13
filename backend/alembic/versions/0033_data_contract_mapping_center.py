"""data contracts and mapping center

Revision ID: 0033_data_contract_mapping
Revises: 0032_operation_catalog
Create Date: 2026-07-13
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0033_data_contract_mapping"
down_revision: str | None = "0032_operation_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "data_contracts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=180), nullable=False),
        sa.Column("kind", sa.String(length=80), nullable=False),
        sa.Column("owner_type", sa.String(length=80), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schema_json", json_type(), nullable=False),
        sa.Column("example_json", json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_data_contracts_name"), "data_contracts", ["name"], unique=False)
    op.create_index(op.f("ix_data_contracts_code"), "data_contracts", ["code"], unique=True)
    op.create_index(op.f("ix_data_contracts_kind"), "data_contracts", ["kind"], unique=False)
    op.create_index(op.f("ix_data_contracts_owner_type"), "data_contracts", ["owner_type"], unique=False)
    op.create_index(op.f("ix_data_contracts_owner_id"), "data_contracts", ["owner_id"], unique=False)

    op.add_column("operation_profiles", sa.Column("request_contract_id", sa.Uuid(), nullable=True))
    op.add_column("operation_profiles", sa.Column("response_contract_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_operation_profiles_request_contract_id"), "operation_profiles", ["request_contract_id"], unique=False)
    op.create_index(op.f("ix_operation_profiles_response_contract_id"), "operation_profiles", ["response_contract_id"], unique=False)
    op.create_foreign_key("fk_operation_profiles_request_contract_id", "operation_profiles", "data_contracts", ["request_contract_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_operation_profiles_response_contract_id", "operation_profiles", "data_contracts", ["response_contract_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "mapping_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=180), nullable=False),
        sa.Column("source_context_json", json_type(), nullable=True),
        sa.Column("target_contract_id", sa.Uuid(), nullable=True),
        sa.Column("operation_profile_id", sa.Uuid(), nullable=True),
        sa.Column("mapping_json", json_type(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("package_id", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["operation_profile_id"], ["operation_profiles.id"], name="fk_mapping_profiles_operation_profile_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_contract_id"], ["data_contracts.id"], name="fk_mapping_profiles_target_contract_id", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mapping_profiles_name"), "mapping_profiles", ["name"], unique=False)
    op.create_index(op.f("ix_mapping_profiles_code"), "mapping_profiles", ["code"], unique=True)
    op.create_index(op.f("ix_mapping_profiles_target_contract_id"), "mapping_profiles", ["target_contract_id"], unique=False)
    op.create_index(op.f("ix_mapping_profiles_operation_profile_id"), "mapping_profiles", ["operation_profile_id"], unique=False)
    op.create_index(op.f("ix_mapping_profiles_package_id"), "mapping_profiles", ["package_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_mapping_profiles_package_id"), table_name="mapping_profiles")
    op.drop_index(op.f("ix_mapping_profiles_operation_profile_id"), table_name="mapping_profiles")
    op.drop_index(op.f("ix_mapping_profiles_target_contract_id"), table_name="mapping_profiles")
    op.drop_index(op.f("ix_mapping_profiles_code"), table_name="mapping_profiles")
    op.drop_index(op.f("ix_mapping_profiles_name"), table_name="mapping_profiles")
    op.drop_table("mapping_profiles")

    op.drop_constraint("fk_operation_profiles_response_contract_id", "operation_profiles", type_="foreignkey")
    op.drop_constraint("fk_operation_profiles_request_contract_id", "operation_profiles", type_="foreignkey")
    op.drop_index(op.f("ix_operation_profiles_response_contract_id"), table_name="operation_profiles")
    op.drop_index(op.f("ix_operation_profiles_request_contract_id"), table_name="operation_profiles")
    op.drop_column("operation_profiles", "response_contract_id")
    op.drop_column("operation_profiles", "request_contract_id")

    op.drop_index(op.f("ix_data_contracts_owner_id"), table_name="data_contracts")
    op.drop_index(op.f("ix_data_contracts_owner_type"), table_name="data_contracts")
    op.drop_index(op.f("ix_data_contracts_kind"), table_name="data_contracts")
    op.drop_index(op.f("ix_data_contracts_code"), table_name="data_contracts")
    op.drop_index(op.f("ix_data_contracts_name"), table_name="data_contracts")
    op.drop_table("data_contracts")
