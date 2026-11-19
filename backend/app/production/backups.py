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


async def list_records(
    session: AsyncSession,
    backup_type: BackupType | str | None = None,
    limit: int = 50,
) -> list[BackupRecord]:
    stmt = select(BackupRecord)
    if backup_type:
        stmt = stmt.where(BackupRecord.backup_type == backup_type)
    stmt = stmt.order_by(BackupRecord.created_at.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


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


async def resolve_backup_dir(session: AsyncSession) -> Path:
    from app.core.config import get_settings
    from app.core.errors import BadRequestError
    from app.environments import repository as environments_repository

    override = None
    environment = await environments_repository.current_environment(session)
    if environment is not None:
        override = next(
            (item.value_json for item in environment.variables if item.key == "BACKUP_DIR" and item.value_json),
            None,
        )
    configured = str(override or get_settings().backup_dir or "").strip()
    if not configured:
        return ensure_export_dir()
    candidate = Path(configured)
    try:
        candidate.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BadRequestError(f"Не удалось создать папку для бэкапов {candidate}: {exc}") from exc
    if not os.access(candidate, os.W_OK):
        raise BadRequestError(f"Папка для бэкапов недоступна для записи: {candidate}")
    return candidate


async def create_db_backup(session: AsyncSession, *, created_by: str | None = None) -> BackupRecord:
    import asyncio
    import shutil

    from sqlalchemy.engine.url import make_url

    from app.core.config import get_settings
    from app.core.errors import BadRequestError

    record = await create_record(session, BackupType.DATABASE_DUMP, created_by=created_by)
    try:
        backup_dir = await resolve_backup_dir(session)
    except BadRequestError as exc:
        await mark_failed(session, record, str(exc))
        raise
    file_path = backup_dir / f"omh-db-{utcnow():%Y%m%d-%H%M%S}-{record.id}.dump"
    database_url = make_url(get_settings().database_url)
    try:
        if database_url.get_backend_name() == "sqlite":
            source = Path(str(database_url.database))
            if source.exists():
                shutil.copyfile(source, file_path)
            else:
                await _sqlite_iterdump(session, file_path)
        else:
            if shutil.which("pg_dump") is None:
                raise BadRequestError("pg_dump не найден на сервере OMH.")
            cmd = [
                "pg_dump",
                "--format=custom",
                "--file", str(file_path),
                "--host", database_url.host or "localhost",
                "--port", str(database_url.port or 5432),
                "--username", database_url.username or "postgres",
                str(database_url.database),
            ]
            env = {**os.environ, "PGPASSWORD": database_url.password or ""}
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            try:
                _, stderr = await asyncio.wait_for(process.communicate(), timeout=300)
            except TimeoutError:
                process.kill()
                await process.wait()
                raise BadRequestError("pg_dump превысил таймаут 300 секунд.")
            if process.returncode != 0:
                raise BadRequestError(f"pg_dump завершился с ошибкой: {stderr.decode(errors='replace')[:1000]}")
        size = file_path.stat().st_size
        import json
        import hashlib
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        checksum = sha256.hexdigest()
        if database_url.get_backend_name() == "postgresql":
            file_path.with_suffix(".meta.json").write_text(json.dumps({"sha256": checksum}), encoding="utf-8")
        format_type = "custom_dump" if file_path.suffix == ".dump" else "sql"
    except BadRequestError as exc:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        await mark_failed(session, record, str(exc))
        raise
    except Exception as exc:
        if file_path.exists():
            file_path.unlink(missing_ok=True)
        await mark_failed(session, record, str(exc))
        raise
    return await mark_success(
        session,
        record,
        file_path=str(file_path),
        size_bytes=size,
        metadata={
            "backup_dir": str(backup_dir),
            "format": format_type,
            "sha256": checksum,
        },
    )


async def _sqlite_iterdump(session: AsyncSession, file_path: Path) -> None:
    """Dump an in-memory or otherwise file-less sqlite database as SQL text."""
    connection = await session.connection()
    raw = await connection.get_raw_connection()
    lines = []
    async for line in raw.driver_connection.iterdump():
        lines.append(line)
    file_path.write_text("\n".join(lines), encoding="utf-8")
