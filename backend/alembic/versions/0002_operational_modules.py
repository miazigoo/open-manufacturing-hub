"""operational modules

Revision ID: 0002_operational_modules
Revises: 0001_core_skeleton
Create Date: 2026-07-02
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_operational_modules"
down_revision: str | None = "0001_core_skeleton"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("incidents", sa.Column("title", sa.String(length=255), nullable=False, server_default="Incident"))
    op.add_column("incidents", sa.Column("severity", sa.String(length=50), nullable=False, server_default="error"))
    op.add_column("incidents", sa.Column("source_system", sa.String(length=255), nullable=True))
    op.add_column("incidents", sa.Column("target_system", sa.String(length=255), nullable=True))
    op.add_column("incidents", sa.Column("failed_step", sa.String(length=255), nullable=True))
    op.add_column("incidents", sa.Column("error_code", sa.String(length=255), nullable=True))
    op.add_column("incidents", sa.Column("normalized_error_message", sa.Text(), nullable=True))
    op.add_column("incidents", sa.Column("affected_events_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("incidents", sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column("incidents", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column("incidents", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_index(op.f("ix_incidents_fingerprint"), "incidents", ["fingerprint"], unique=True)

    op.create_table(
        "incident_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("incident_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("step_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["integration_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["event_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["step_id"], ["event_steps.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_incident_events_incident_event", "incident_events", ["incident_id", "event_id"], unique=True)
    op.create_index(op.f("ix_incident_events_event_id"), "incident_events", ["event_id"], unique=False)
    op.create_index(op.f("ix_incident_events_incident_id"), "incident_events", ["incident_id"], unique=False)

    op.create_table(
        "sites",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "health_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("component_type", sa.String(length=50), nullable=False),
        sa.Column("component_name", sa.String(length=255), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_health_checks_component_name"), "health_checks", ["component_name"], unique=False)
    op.create_index(op.f("ix_health_checks_site_id"), "health_checks", ["site_id"], unique=False)
    op.create_table(
        "agent_heartbeats",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=False),
        sa.Column("agent_name", sa.String(length=255), nullable=False),
        sa.Column("internet_ok", sa.Boolean(), nullable=True),
        sa.Column("can_reach_hub", sa.Boolean(), nullable=True),
        sa.Column("can_reach_wms", sa.Boolean(), nullable=True),
        sa.Column("can_reach_erp", sa.Boolean(), nullable=True),
        sa.Column("local_ip", sa.String(length=100), nullable=True),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_heartbeats_site_id"), "agent_heartbeats", ["site_id"], unique=False)

    op.create_table(
        "notification_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("trigger_type", sa.String(length=100), nullable=False),
        sa.Column("filters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("channels_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=True),
        sa.Column("trigger_type", sa.String(length=100), nullable=False),
        sa.Column("target_channel", sa.String(length=100), nullable=False),
        sa.Column("target_address", sa.String(length=1024), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_deliveries_rule_id"), "notification_deliveries", ["rule_id"], unique=False)

    op.create_table(
        "maintenance_windows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("component_type", sa.String(length=100), nullable=False),
        sa.Column("component_name", sa.String(length=255), nullable=False),
        sa.Column("site_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_maintenance_windows_component_name"), "maintenance_windows", ["component_name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_maintenance_windows_component_name"), table_name="maintenance_windows")
    op.drop_table("maintenance_windows")
    op.drop_index(op.f("ix_notification_deliveries_rule_id"), table_name="notification_deliveries")
    op.drop_table("notification_deliveries")
    op.drop_table("notification_rules")
    op.drop_index(op.f("ix_agent_heartbeats_site_id"), table_name="agent_heartbeats")
    op.drop_table("agent_heartbeats")
    op.drop_index(op.f("ix_health_checks_site_id"), table_name="health_checks")
    op.drop_index(op.f("ix_health_checks_component_name"), table_name="health_checks")
    op.drop_table("health_checks")
    op.drop_table("sites")
    op.drop_index(op.f("ix_incident_events_incident_id"), table_name="incident_events")
    op.drop_index(op.f("ix_incident_events_event_id"), table_name="incident_events")
    op.drop_index("ix_incident_events_incident_event", table_name="incident_events")
    op.drop_table("incident_events")
    op.drop_index(op.f("ix_incidents_fingerprint"), table_name="incidents")
    for column in ["updated_at", "resolved_at", "acknowledged_at", "last_seen_at", "first_seen_at", "affected_events_count", "normalized_error_message", "error_code", "failed_step", "target_system", "source_system", "severity", "title"]:
        op.drop_column("incidents", column)
