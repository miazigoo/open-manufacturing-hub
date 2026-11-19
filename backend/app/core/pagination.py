from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel

T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False


def encode_cursor(created_at: datetime, item_id: UUID) -> str:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    payload = {
        "v": 1,
        "ts": created_at.isoformat(),
        "id": str(item_id),
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("v") != 1:
            raise ValueError("Unsupported cursor version")
        ts_str = payload["ts"]
        id_str = payload["id"]
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        item_id = UUID(id_str)
        return dt, item_id
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid cursor format: {exc}",
        ) from exc


def encode_sort_cursor(sort_field: str, val: Any, item_id: UUID, scope: list) -> str:
    payload = {
        "v": 3, "s": sort_field, "scope": scope,
        "val": val.isoformat() if isinstance(val, datetime) else val, "id": str(item_id),
    }
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()


def decode_sort_cursor(cursor: str, sort_field: str, scope: list) -> tuple[Any, UUID]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        if payload["v"] != 3 or payload["s"] != sort_field or payload["scope"] != scope:
            raise ValueError("Cursor does not match the current filters and sort")
        val = payload["val"]
        if sort_field in ("priority", "attempts"):
            if type(val) is not int:
                raise ValueError("Expected an integer")
        elif val is not None or sort_field != "next_retry_at":
            val = datetime.fromisoformat(val)
            if val.tzinfo is None:
                val = val.replace(tzinfo=timezone.utc)
        return val, UUID(payload["id"])
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        raise HTTPException(status_code=422, detail="Invalid page cursor") from exc
