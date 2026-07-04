from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TransformDefinition(BaseModel):
    name: str
    category: str
    description: str
    args_schema: dict[str, Any] = Field(default_factory=dict)


class TransformStep(BaseModel):
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class TransformTraceItem(BaseModel):
    transform: str
    before: Any = None
    after: Any = None
    args: dict[str, Any] = Field(default_factory=dict)


class TransformResult(BaseModel):
    success: bool
    value: Any = None
    error_code: str | None = None
    error_message: str | None = None
    trace: list[TransformTraceItem] = Field(default_factory=list)


class TransformTestRequest(BaseModel):
    value: Any = None
    chain: list[TransformStep] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class TransformTestResponse(BaseModel):
    success: bool
    result: Any = None
    error_code: str | None = None
    error_message: str | None = None
    trace: list[TransformTraceItem] = Field(default_factory=list)
