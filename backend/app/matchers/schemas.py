from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

MATCHER_TYPES = {
    "body_path_equals", "body_path_not_equals", "body_path_exists", "body_path_contains", "body_path_not_contains",
    "body_path_in", "body_path_not_in", "body_path_starts_with", "body_path_ends_with",
    "body_path_gt", "body_path_lt", "body_path_ge", "body_path_le", "body_path_regex",
    "header_equals", "query_equals", "xml_path_equals", "xml_path_exists", "xml_contains",
    "text_contains", "regex", "always",
}
MATCHER_MODES = {"all", "any", "none"}
MAX_GROUP_DEPTH = 3


class MatcherRule(BaseModel):
    type: str | None = None
    path: str | None = None
    value: Any = None
    values: list[Any] | None = None
    pattern: str | None = None
    group: "MatcherGroup | None" = None


class MatcherGroup(BaseModel):
    mode: str = "all"
    rules: list[MatcherRule] = Field(default_factory=list)


MatcherRule.model_rebuild()


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
    mode: str | None = None
    trace: list["MatcherTraceItem"] | None = None


MatcherTraceItem.model_rebuild()


class MatcherTestResponse(BaseModel):
    matched: bool
    trace: list[MatcherTraceItem]
