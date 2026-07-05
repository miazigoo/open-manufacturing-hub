from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import BackupStatus, BackupType
from app.core.errors import NotFoundError
from app.production.models import BackupRecord

BACKUP_ROOT = Path("backups")
EXPORT_DIR = BACKUP_ROOT / "config"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def create_record(session: AsyncSession, backup_type: BackupType, *, created_by: str | None = None, metadata: dict | None = None) -> BackupRecord:
    record = BackupRecord(backup_type=backup_type, status=BackupStatus.RUNNING, created_by=created_by, metadata_json=metadata or {})
    session.add(record)
    await session.flush()
    return record


async def mark_success(session: AsyncSession, record: BackupRecord, *, file_path: str | None, size_bytes: int | None, metadata: dict | None = None) -> BackupRecord:
    record.status = BackupStatus.SUCCESS
    record.file_path = file_path
    record.size_bytes = size_bytes
    record.finished_at = utcnow()
    if metadata:
        record.metadata_json = {**(record.metadata_json or {}), **metadata}
    await session.flush()
    return record


async def mark_failed(session: AsyncSession, record: BackupRecord, error: str) -> BackupRecord:
    record.status = BackupStatus.FAILED
    record.error_message = error
    record.finished_at = utcnow()
    await session.flush()
    return record


async def list_records(session: AsyncSession) -> list[BackupRecord]:
    return list((await session.execute(select(BackupRecord).order_by(BackupRecord.created_at.desc()))).scalars().all())


async def get_record(session: AsyncSession, record_id: UUID) -> BackupRecord:
    record = await session.get(BackupRecord, record_id)
    if record is None:
        raise NotFoundError("Backup record not found")
    return record


async def last_success(session: AsyncSession, backup_type: BackupType | None = None) -> BackupRecord | None:
    query = select(BackupRecord).where(BackupRecord.status == BackupStatus.SUCCESS).order_by(BackupRecord.created_at.desc()).limit(1)
    if backup_type:
        query = query.where(BackupRecord.backup_type == backup_type)
    return (await session.execute(query)).scalar_one_or_none()


async def recent_success_exists(session: AsyncSession, hours: int = 24) -> bool:
    cutoff = utcnow() - timedelta(hours=hours)
    item = (await session.execute(select(BackupRecord.id).where(BackupRecord.status == BackupStatus.SUCCESS, BackupRecord.created_at >= cutoff).limit(1))).scalar_one_or_none()
    return item is not None


def ensure_export_dir() -> Path:
    for candidate in (EXPORT_DIR, Path(tempfile.gettempdir()) / "open-manufacturing-hub" / "backups" / "config"):
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            if os.access(candidate, os.W_OK):
                return candidate
        except OSError:
            continue
    raise PermissionError("No writable export directory available")
