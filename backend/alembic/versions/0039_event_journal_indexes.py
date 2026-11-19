"""event journal pagination indexes

Revision ID: 0039_event_journal_indexes
Revises: 0038_federation
Create Date: 2026-11-19
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0039_event_journal_indexes"
down_revision: str | None = "0038_federation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_integration_events_created_id",
        "integration_events",
        ["created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_integration_events_entity_id",
        "integration_events",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        "ix_integration_queue_event_created",
        "integration_queue_messages",
        ["event_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_integration_queue_event_created", table_name="integration_queue_messages")
    op.drop_index("ix_integration_events_entity_id", table_name="integration_events")
    op.drop_index("ix_integration_events_created_id", table_name="integration_events")
