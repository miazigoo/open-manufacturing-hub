#!/usr/bin/env python3
"""Verify a trusted OMH PostgreSQL backup on the isolated recovery instance."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse
from uuid import uuid4

import asyncpg


def detect_format(file_path: Path) -> str:
    with file_path.open("rb") as stream:
        if stream.read(5) == b"PGDMP":
            return "custom"
    if file_path.suffix.lower() == ".sql":
        return "sql"
    raise ValueError("Expected plain .sql or a PostgreSQL custom dump")


def verify_checksum(file_path: Path, meta_path: Path | None = None) -> tuple[str, bool | None]:
    with file_path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if meta_path is None:
        candidates = [Path(str(file_path) + ".meta.json"), file_path.with_suffix(".meta.json")]
        meta_path = next((path for path in candidates if path.exists()), None)
    if meta_path is None:
        return actual, None
    meta = json.loads(meta_path.read_text())
    expected = next((meta[key] for key in ("sha256", "file_sha256", "db_sha256", "checksum") if meta.get(key)), None)
    if not expected or actual.lower() != str(expected).strip().lower():
        raise ValueError("Checksum verification failed")
    return actual, True


def validate_target_db(target_db: str, production_db: str | None) -> None:
    normalized = target_db.strip().lower()
    if not normalized:
        raise ValueError("Target database name cannot be empty")
    if normalized in {"postgres", "template0", "template1"}:
        raise ValueError("Refusing a system database")
    if production_db and normalized == production_db.strip().lower():
        raise ValueError("SAFETY VIOLATION: target matches source database")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", target_db):
        raise ValueError("Invalid target database identifier")


def parse_db_connection(database_url=None, host=None, port=None, user=None, password=None, db=None):
    url = urlparse(database_url or os.getenv("OMH_DATABASE_URL") or os.getenv("DATABASE_URL") or "")
    return {
        "host": host or os.getenv("POSTGRES_HOST") or url.hostname or "localhost",
        "port": int(port or os.getenv("POSTGRES_PORT") or url.port or 5432),
        "user": user or os.getenv("POSTGRES_USER") or unquote(url.username or "omh"),
        "password": password or os.getenv("POSTGRES_PASSWORD") or unquote(url.password or ""),
        "production_db": db or os.getenv("POSTGRES_DB") or unquote(url.path.lstrip("/")) or "omh",
    }


async def run_restore_drill(file_path: Path, target_db=None, meta_path=None, keep_db=False, db_config=None):
    if not file_path.is_file():
        raise FileNotFoundError(file_path)
    config = db_config or parse_db_connection()
    target_db = target_db or f"omh_restore_drill_{uuid4().hex}"
    validate_target_db(target_db, config["production_db"])
    digest, verified = verify_checksum(file_path, meta_path)
    fmt = detect_format(file_path)
    connection = {key: config[key] for key in ("host", "port", "user", "password")}
    started = time.monotonic()
    admin = await asyncpg.connect(database="postgres", **connection)
    created = False
    success = False
    try:
        # CREATE is the ownership boundary. Concurrent or pre-existing targets fail here.
        await admin.execute(f'CREATE DATABASE "{target_db}" TEMPLATE template0')
        created = True
        common = ["-h", config["host"], "-p", str(config["port"]), "-U", config["user"], "-d", target_db]
        if fmt == "custom":
            command = ["pg_restore", "--exit-on-error", *common, str(file_path)]
        else:
            command = ["psql", "-X", "-v", "ON_ERROR_STOP=1", *common, "-f", str(file_path)]
        proc = await asyncio.create_subprocess_exec(
            *command, env={**os.environ, "PGPASSWORD": config["password"]},
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode:
            raise RuntimeError(f"Restore failed ({proc.returncode}): {stderr.decode(errors='replace')[-1000:]}")
        restored = await asyncpg.connect(database=target_db, **connection)
        try:
            revision = await restored.fetchval("SELECT version_num FROM alembic_version")
            if not revision:
                raise ValueError("Missing OMH migration revision")
            counts = {}
            for table in ("integration_events", "event_runs", "artifacts", "integration_queue_messages", "audit_events"):
                counts[table] = await restored.fetchval(f'SELECT count(*) FROM "{table}"')
            tables = await restored.fetchval("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
        finally:
            await restored.close()
        success = True
        return dict(status="success", target_db=target_db, production_db=config["production_db"], file=str(file_path),
                    file_format=fmt, sha256=digest, checksum_verified=verified, alembic_version=revision,
                    counts=counts, tables_count=tables, cleaned_up=not keep_db,
                    restore_duration_seconds=round(time.monotonic() - started, 3))
    finally:
        try:
            if created and (not success or not keep_db):
                await admin.execute(f'DROP DATABASE "{target_db}" WITH (FORCE)')
        finally:
            await admin.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", "-f", type=Path, required=True)
    parser.add_argument("--target-db")
    parser.add_argument("--meta", type=Path)
    parser.add_argument("--keep-db", action="store_true")
    for option in ("host", "port", "user", "password", "db"):
        parser.add_argument("--" + option)
    args = parser.parse_args()
    config = parse_db_connection(host=args.host, port=args.port, user=args.user, password=args.password, db=args.db)
    try:
        result = asyncio.run(run_restore_drill(args.file, args.target_db, args.meta, args.keep_db, config))
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
