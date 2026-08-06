from __future__ import annotations

import re
import time
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record_action
from app.core.database import get_session
from app.core.errors import BadRequestError

router = APIRouter(prefix="/api/sql-console", tags=["sql-console"])

FORBIDDEN_RE = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|call|execute|copy|vacuum|analyze|comment|set|reset|listen|notify|unlisten|do|lock)\b",
    re.IGNORECASE,
)
DEFAULT_LIMIT = 200
MAX_LIMIT = 1000
STATEMENT_TIMEOUT_MS = 10_000


class SqlQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)


class SqlQueryResponse(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    elapsed_ms: int


def validate_query(query: str) -> str:
    cleaned = query.strip().rstrip(";").strip()
    if not cleaned:
        raise BadRequestError("Пустой запрос.")
    if ";" in cleaned:
        raise BadRequestError("Разрешен только один запрос за раз (без точки с запятой в середине).")
    first_word = cleaned.split(None, 1)[0].lower()
    if first_word not in {"select", "with", "values", "table", "show"}:
        raise BadRequestError("SQL-консоль только для чтения: разрешены SELECT-запросы.")
    if first_word == "show":
        raise BadRequestError("SHOW не поддерживается, используйте SELECT.")
    match = FORBIDDEN_RE.search(cleaned)
    if match:
        raise BadRequestError(f"Запрещенное слово в запросе только для чтения: {match.group(0).upper()}. Разрешен только SELECT.")
    return cleaned


@router.post("/query", response_model=SqlQueryResponse)
async def run_query(payload: SqlQueryRequest, session: AsyncSession = Depends(get_session)):
    query = validate_query(payload.query)
    wrapped = f"SELECT * FROM ({query}) AS omh_sql_console LIMIT {int(payload.limit) + 1}"
    started = time.monotonic()
    try:
        bind = session.bind
        if bind is not None and bind.dialect.name == "postgresql":
            await session.execute(text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"))
        result = await session.execute(text(wrapped))
    except Exception as exc:
        await session.rollback()
        raise BadRequestError(f"Запрос не выполнен: {exc}") from exc
    elapsed_ms = int((time.monotonic() - started) * 1000)
    columns = list(result.keys())
    raw_rows = result.mappings().all()
    truncated = len(raw_rows) > payload.limit
    rows = [{column: _jsonable(row[column]) for column in columns} for row in raw_rows[: payload.limit]]
    await record_action(
        session,
        action="sql_console_query",
        category="sql_console",
        summary=f"SQL-консоль: {len(rows)} строк за {elapsed_ms} мс",
        details={"query": query[:2000], "row_count": len(rows), "truncated": truncated},
    )
    await session.commit()
    return SqlQueryResponse(columns=columns, rows=rows, row_count=len(rows), truncated=truncated, elapsed_ms=elapsed_ms)


def _jsonable(value: Any) -> Any:
    import datetime as _dt
    import uuid as _uuid

    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat()
    if isinstance(value, _uuid.UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value
