from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class JsonFieldMapping(BaseModel):
    target: str
    mode: Literal["path", "constant", "template"] = "path"
    value: Any
    transforms: list[dict[str, Any]] = Field(default_factory=list)


class JsonBuildRequest(BaseModel):
    template: dict[str, Any] | None = None
    fields: list[JsonFieldMapping] = Field(default_factory=list)
    scope: dict[str, Any] = Field(default_factory=dict)


class JsonBuildResponse(BaseModel):
    result: dict[str, Any]
