from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LocalizedText = dict[str, str]
CoverageStatus = Literal["ready", "partial", "planned", "missing", "missing_docs", "missing_wizard"]
DimensionStatus = Literal["ready", "partial", "planned", "missing", "missing_docs", "missing_wizard", "missing_training", "not_applicable"]
Complexity = Literal["basic", "intermediate", "advanced"]


class CoverageDimensionStatuses(BaseModel):
    wizard: DimensionStatus
    docs: DimensionStatus
    training: DimensionStatus
    troubleshooting: DimensionStatus
    e2e: DimensionStatus


class CoverageChecklistItem(BaseModel):
    label: str
    status: DimensionStatus
    link: str | None = None
    note: str | None = None


class PackageCoverageStatus(BaseModel):
    package_id: str
    installed: bool
    enabled: bool
    warning: str | None = None


class IntegrationCoverageItem(BaseModel):
    requirement_id: str
    title: LocalizedText
    description: LocalizedText
    category: str
    source_systems: list[str]
    source_summary: LocalizedText
    input_modes: list[str]
    input_summary: LocalizedText
    omh_actions: list[str]
    omh_actions_summary: LocalizedText
    result_summary: LocalizedText
    runtime_needs: list[str] = Field(default_factory=list)
    personas: list[str] = Field(default_factory=list)
    complexity: Complexity = "intermediate"
    required_capabilities: list[str] = Field(default_factory=list)
    recommended_pattern: str | None = None
    recommended_tool: LocalizedText = Field(default_factory=dict)
    wizard_route: str | None = None
    workbench_route: str | None = None
    docs_links: list[str] = Field(default_factory=list)
    recipe_link: str | None = None
    training_example_ids: list[str] = Field(default_factory=list)
    troubleshooting_links: list[str] = Field(default_factory=list)
    e2e_tests: list[str] = Field(default_factory=list)
    test_case_ids: list[str] = Field(default_factory=list)
    package_requirements: list[str] = Field(default_factory=list)
    statuses: CoverageDimensionStatuses
    status: CoverageStatus
    readiness_score: int = Field(ge=0, le=100)
    gaps: list[str] = Field(default_factory=list)
    checklist: list[CoverageChecklistItem] = Field(default_factory=list)
    package_statuses: list[PackageCoverageStatus] = Field(default_factory=list)
    show_in_integration_start: bool = True


class IntegrationCoverageSummary(BaseModel):
    total: int
    ready: int
    partial: int
    planned: int
    missing: int
    missing_docs: int
    missing_wizard: int
    average_readiness: int
    by_status: dict[str, int]
    by_persona: dict[str, int]


class IntegrationCoverageResponse(BaseModel):
    summary: IntegrationCoverageSummary
    items: list[IntegrationCoverageItem]


class IntegrationCoverageReportResponse(BaseModel):
    markdown: str
