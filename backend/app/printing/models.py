from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, new_uuid
from app.core.enums import PrintJobStatus, PrintLineStatus

JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")


class PrintPrinter(TimestampMixin, Base):
    __tablename__ = "print_printers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    connector_id: Mapped[UUID] = mapped_column(ForeignKey("connector_instances.id", ondelete="RESTRICT"), nullable=False, index=True)
    dpi: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    settings_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    jobs: Mapped[list["PrintJob"]] = relationship(back_populates="printer", lazy="selectin")


class PrintJob(TimestampMixin, Base):
    __tablename__ = "print_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    job_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    printer_id: Mapped[UUID] = mapped_column(ForeignKey("print_printers.id", ondelete="RESTRICT"), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(255), nullable=False)
    source_document_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_document_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[PrintJobStatus] = mapped_column(
        Enum(PrintJobStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=PrintJobStatus.READY,
        nullable=False,
        index=True,
    )
    label_settings_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    total_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sent_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    printed_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    printer: Mapped[PrintPrinter] = relationship(back_populates="jobs", lazy="selectin")
    lines: Mapped[list["PrintJobLine"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PrintJobLine.sequence_no",
    )


class PrintJobLine(TimestampMixin, Base):
    __tablename__ = "print_job_lines"
    __table_args__ = (
        Index("ix_print_job_lines_job_sequence", "job_id", "sequence_no", unique=True),
        Index("ix_print_job_lines_job_status", "job_id", "status"),
        Index("ix_print_job_lines_unique_code", "job_id", "code_sha256", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("print_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    code_visible: Mapped[str] = mapped_column(Text, nullable=False)
    code_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    zpl: Mapped[str] = mapped_column(Text, nullable=False)
    zpl_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[PrintLineStatus] = mapped_column(
        Enum(PrintLineStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        default=PrintLineStatus.NEW,
        nullable=False,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    printed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    job: Mapped[PrintJob] = relationship(back_populates="lines")


class PrintJobLog(Base):
    __tablename__ = "print_job_logs"
    __table_args__ = (
        Index("ix_print_job_logs_job_created", "job_id", "created_at"),
        Index("ix_print_job_logs_line_created", "line_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("print_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    line_id: Mapped[UUID | None] = mapped_column(ForeignKey("print_job_lines.id", ondelete="CASCADE"), nullable=True, index=True)
    sequence_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON_TYPE, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
