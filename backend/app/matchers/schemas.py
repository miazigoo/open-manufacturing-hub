from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

MATCHER_TYPES = {
    "body_path_equals", "body_path_exists", "body_path_contains", "body_path_in",
    "header_equals", "query_equals", "xml_path_equals", "xml_path_exists", "xml_contains",
    "text_contains", "regex", "always",
}
MATCHER_MODES = {"all", "any", "none"}


class MatcherRule(BaseModel):
    type: str
    path: str | None = None
    value: Any = None
    values: list[Any] | None = None
    pattern: str | None = None


class MatcherGroup(BaseModel):
    mode: str = "all"
    rules: list[MatcherRule] = Field(default_factory=list)


class MatcherTestRequest(BaseModel):
    input_mode: str = "json"
    payload: Any = None
    text: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    query: dict[str, str] = Field(default_factory=dict)
    matcher_group: MatcherGroup | dict[str, Any]


class MatcherTraceItem(BaseModel):
    rule: str
    path: str | None = None
    actual: Any = None
    expected: Any = None
    matched: bool
    message: str | None = None


class MatcherTestResponse(BaseModel):
    matched: bool
    trace: list[MatcherTraceItem]
