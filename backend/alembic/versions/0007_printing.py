"""printing jobs

Revision ID: 0007_printing
Revises: 0006_onec_polling
Create Date: 2026-07-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_printing"
down_revision: str | None = "0006_onec_polling"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "print_printers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("connector_id", sa.Uuid(), nullable=False),
        sa.Column("dpi", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("settings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["connector_id"], ["connector_instances.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_print_printers_connector_id"), "print_printers", ["connector_id"], unique=False)
    op.create_index(op.f("ix_print_printers_name"), "print_printers", ["name"], unique=True)

    op.create_table(
        "print_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_key", sa.String(length=255), nullable=False),
        sa.Column("printer_id", sa.Uuid(), nullable=False),
        sa.Column("source_system", sa.String(length=255), nullable=False),
        sa.Column("source_document_id", sa.String(length=255), nullable=True),
        sa.Column("source_document_name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.Enum("draft", "ready", "printing", "partially_sent", "sent", "partially_printed", "printed", "error", "cancelled", native_enum=False), nullable=False),
        sa.Column("label_settings_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("total_lines", sa.Integer(), nullable=False),
        sa.Column("sent_lines", sa.Integer(), nullable=False),
        sa.Column("printed_lines", sa.Integer(), nullable=False),
        sa.Column("error_lines", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["printer_id"], ["print_printers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_key"),
    )
    op.create_index(op.f("ix_print_jobs_job_key"), "print_jobs", ["job_key"], unique=True)
    op.create_index(op.f("ix_print_jobs_printer_id"), "print_jobs", ["printer_id"], unique=False)
    op.create_index(op.f("ix_print_jobs_source_document_id"), "print_jobs", ["source_document_id"], unique=False)
    op.create_index(op.f("ix_print_jobs_status"), "print_jobs", ["status"], unique=False)

    op.create_table(
        "print_job_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("code_visible", sa.Text(), nullable=False),
        sa.Column("code_sha256", sa.String(length=64), nullable=False),
        sa.Column("zpl", sa.Text(), nullable=False),
        sa.Column("zpl_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.Enum("new", "reserved", "test_mode", "sent_to_printer", "printed", "error", "return_to_print", "cancelled", native_enum=False), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("printed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["print_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_print_job_lines_job_id"), "print_job_lines", ["job_id"], unique=False)
    op.create_index("ix_print_job_lines_job_sequence", "print_job_lines", ["job_id", "sequence_no"], unique=True)
    op.create_index("ix_print_job_lines_job_status", "print_job_lines", ["job_id", "status"], unique=False)
    op.create_index("ix_print_job_lines_unique_code", "print_job_lines", ["job_id", "code_sha256"], unique=True)
    op.create_index(op.f("ix_print_job_lines_status"), "print_job_lines", ["status"], unique=False)

    op.create_table(
        "print_job_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("line_id", sa.Uuid(), nullable=True),
        sa.Column("sequence_no", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=80), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("details_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["print_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["line_id"], ["print_job_lines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_print_job_logs_job_id"), "print_job_logs", ["job_id"], unique=False)
    op.create_index(op.f("ix_print_job_logs_line_id"), "print_job_logs", ["line_id"], unique=False)
    op.create_index("ix_print_job_logs_job_created", "print_job_logs", ["job_id", "created_at"], unique=False)
    op.create_index("ix_print_job_logs_line_created", "print_job_logs", ["line_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_print_job_logs_line_created", table_name="print_job_logs")
    op.drop_index("ix_print_job_logs_job_created", table_name="print_job_logs")
    op.drop_index(op.f("ix_print_job_logs_line_id"), table_name="print_job_logs")
    op.drop_index(op.f("ix_print_job_logs_job_id"), table_name="print_job_logs")
    op.drop_table("print_job_logs")
    op.drop_index(op.f("ix_print_job_lines_status"), table_name="print_job_lines")
    op.drop_index("ix_print_job_lines_unique_code", table_name="print_job_lines")
    op.drop_index("ix_print_job_lines_job_status", table_name="print_job_lines")
    op.drop_index("ix_print_job_lines_job_sequence", table_name="print_job_lines")
    op.drop_index(op.f("ix_print_job_lines_job_id"), table_name="print_job_lines")
    op.drop_table("print_job_lines")
    op.drop_index(op.f("ix_print_jobs_status"), table_name="print_jobs")
    op.drop_index(op.f("ix_print_jobs_source_document_id"), table_name="print_jobs")
    op.drop_index(op.f("ix_print_jobs_printer_id"), table_name="print_jobs")
    op.drop_index(op.f("ix_print_jobs_job_key"), table_name="print_jobs")
    op.drop_table("print_jobs")
    op.drop_index(op.f("ix_print_printers_name"), table_name="print_printers")
    op.drop_index(op.f("ix_print_printers_connector_id"), table_name="print_printers")
    op.drop_table("print_printers")
