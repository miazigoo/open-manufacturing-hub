from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

RuleSetScope = Literal["global", "workflow", "integration_flow", "package"]


class BusinessRuleSetBase(BaseModel):
    name: str
    description: str | None = None
    enabled: bool = True
    scope: RuleSetScope | None = "global"
    rules_json: dict[str, Any] = Field(default_factory=lambda: {"mode": "first_match", "rules": []})


class BusinessRuleSetCreate(BusinessRuleSetBase):
    pass


class BusinessRuleSetPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    scope: RuleSetScope | None = None
    rules_json: dict[str, Any] | None = None


class BusinessRuleSetRead(BusinessRuleSetBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BusinessRuleTestRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    rules_json: dict[str, Any] | None = None


class RuleEvaluationResult(BaseModel):
    success: bool
    matched_rules: list[str] = Field(default_factory=list)
    actions_applied: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "continue"
    error_code: str | None = None
    error_message: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    variables: dict[str, Any] = Field(default_factory=dict)
    target_system: str | None = None
    operation: str | None = None
    route: str | None = None
    skip_steps: list[str] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)
