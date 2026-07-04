from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class UIOption(BaseModel):
    id: str
    label: str
    type: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class UIPackageState(BaseModel):
    package_id: str
    installed: bool
    enabled: bool
    status: str | None = None
    action_label: str


class UICockpitSummary(BaseModel):
    package_state: UIPackageState
    metrics: dict[str, int]
    quick_actions: list[dict[str, Any]]
    integrations: list[dict[str, Any]]
    connection_health: list[dict[str, Any]]
    recent_events: list[dict[str, Any]]


class UICockpitOptions(BaseModel):
    package_state: UIPackageState
    connectors: list[UIOption]
    onec_connectors: list[UIOption]
    rest_connectors: list[UIOption]
    printer_connectors: list[UIOption]
    operation_templates: list[UIOption]
    odata_lookup_templates: list[UIOption]
    scenario_presets: list[dict[str, Any]]
    input_modes: list[str]
    response_modes: list[str]


class UIFlowBuilderOptions(BaseModel):
    package_state: UIPackageState
    connectors: list[UIOption]
    onec_connectors: list[UIOption]
    rest_connectors: list[UIOption]
    printer_connectors: list[UIOption]
    operation_templates: list[UIOption]
    odata_lookup_templates: list[UIOption]
    matcher_types: list[str]
    action_types: list[str]
    available_steps: list[dict[str, str]]
    saved_test_cases: list[UIOption]


class UIFlowBuilderState(BaseModel):
    flow_id: UUID
    flow: dict[str, Any]
    builder_json: dict[str, Any]
    options: UIFlowBuilderOptions


class UINavigationItem(BaseModel):
    group: str
    title: str
    route: str
    package_id: str | None = None
    enabled: bool = True
    advanced: bool = False
