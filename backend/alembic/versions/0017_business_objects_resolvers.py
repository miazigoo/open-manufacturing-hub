"""business objects resolver engine v2

Revision ID: 0017_business_objects_resolvers
Revises: 0016_queue_first_runtime
Create Date: 2026-07-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0017_business_objects_resolvers"
down_revision: str | None = "0016_queue_first_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_type():
    return postgresql.JSONB(astext_type=sa.Text())


def upgrade() -> None:
    op.create_table(
        "resolver_definitions_v2",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("resolver_code", sa.String(length=160), nullable=False),
        sa.Column("object_type", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("strategy", sa.String(length=40), nullable=False),
        sa.Column("connector_id", sa.Uuid(), nullable=True),
        sa.Column("input_schema_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_schema_json", json_type(), nullable=True),
        sa.Column("config_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("cache_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("cache_ttl_seconds", sa.Integer(), nullable=False, server_default="3600"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["connector_instances.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_resolver_definitions_v2_name"),
        sa.UniqueConstraint("resolver_code", name="uq_resolver_definitions_v2_code"),
    )
    for column in ("name", "resolver_code", "object_type", "enabled", "strategy", "connector_id"):
        op.create_index(op.f(f"ix_resolver_definitions_v2_{column}"), "resolver_definitions_v2", [column])
    op.create_index("ix_resolver_definitions_v2_object_strategy", "resolver_definitions_v2", ["object_type", "strategy"])

    op.create_table(
        "resolver_cache_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resolver_id", sa.Uuid(), nullable=False),
        sa.Column("resolver_code", sa.String(length=160), nullable=False),
        sa.Column("cache_key", sa.String(length=500), nullable=False),
        sa.Column("input_hash", sa.String(length=128), nullable=False),
        sa.Column("object_type", sa.String(length=120), nullable=False),
        sa.Column("resolved_object_json", json_type(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_connector_id", sa.Uuid(), nullable=True),
        sa.Column("source_system", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["resolver_id"], ["resolver_definitions_v2.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_connector_id"], ["connector_instances.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resolver_id", "cache_key", name="uq_resolver_cache_resolver_key"),
    )
    for column in ("resolver_id", "resolver_code", "cache_key", "input_hash", "object_type", "source_connector_id", "source_system", "expires_at"):
        op.create_index(op.f(f"ix_resolver_cache_entries_{column}"), "resolver_cache_entries", [column])
    op.create_index("ix_resolver_cache_code_key", "resolver_cache_entries", ["resolver_code", "cache_key"])
    op.create_index("ix_resolver_cache_object_expires", "resolver_cache_entries", ["object_type", "expires_at"])


def downgrade() -> None:
    op.drop_table("resolver_cache_entries")
    op.drop_table("resolver_definitions_v2")
