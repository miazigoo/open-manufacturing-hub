from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ResolvePathRequest(BaseModel):
    data: dict[str, Any]
    path: str


class ResolvePathResponse(BaseModel):
    value: Any | None = None
    error: str | None = None
