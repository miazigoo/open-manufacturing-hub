from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.integration_coverage.registry import REQUIREMENT_DEFINITIONS
from app.integration_coverage.schemas import (
    CoverageChecklistItem,
    CoverageDimensionStatuses,
    DimensionStatus,
    IntegrationCoverageItem,
    IntegrationCoverageResponse,
    IntegrationCoverageSummary,
    PackageCoverageStatus,
)
from app.integration_patterns import service as pattern_service
from app.packages import repository as package_repository

WEIGHTS = {"wizard": 25, "docs": 25, "training": 15, "troubleshooting": 15, "e2e": 20}
PARTIAL_RATIO = 0.5
ACCEPTABLE_PATTERN_STATUSES = {"ready", "partial", "missing_docs"}


def list_static_items() -> list[IntegrationCoverageItem]:
    return [_build_item(definition) for definition in REQUIREMENT_DEFINITIONS]


async def list_coverage(session: AsyncSession) -> IntegrationCoverageResponse:
    items = await _with_package_statuses(session, list_static_items())
    return IntegrationCoverageResponse(summary=build_summary(items), items=items)


async def get_requirement(session: AsyncSession, requirement_id: str) -> IntegrationCoverageItem:
    for item in await _with_package_statuses(session, list_static_items()):
        if item.requirement_id == requirement_id:
            return item
    raise NotFoundError("Integration coverage requirement not found")


async def get_summary(session: AsyncSession) -> IntegrationCoverageSummary:
    response = await list_coverage(session)
    return response.summary


def build_summary(items: Iterable[IntegrationCoverageItem]) -> IntegrationCoverageSummary:
    item_list = list(items)
    by_status = Counter(item.status for item in item_list)
    by_persona: Counter[str] = Counter()
    for item in item_list:
        by_persona.update(item.personas or ["unassigned"])
    total = len(item_list)
    average = round(sum(item.readiness_score for item in item_list) / total) if total else 0
    return IntegrationCoverageSummary(
        total=total,
        ready=by_status.get("ready", 0),
        partial=by_status.get("partial", 0),
        planned=by_status.get("planned", 0),
        missing=by_status.get("missing", 0),
        missing_docs=by_status.get("missing_docs", 0),
        missing_wizard=by_status.get("missing_wizard", 0),
        average_readiness=average,
        by_status=dict(sorted(by_status.items())),
        by_persona=dict(sorted(by_persona.items())),
    )


def build_report(items: list[IntegrationCoverageItem] | None = None) -> str:
    item_list = items or list_static_items()
    summary = build_summary(item_list)
    lines = [
        "# Integration Requirements Coverage Report",
        "",
        "Generated from `backend/app/integration_coverage/registry.py`.",
        "",
        "## Summary",
        "",
        f"- Total requirements: {summary.total}",
        f"- Ready: {summary.ready}",
        f"- Partial: {summary.partial}",
        f"- Planned: {summary.planned}",
        f"- Missing docs: {summary.missing_docs}",
        f"- Missing wizard: {summary.missing_wizard}",
        f"- Average readiness: {summary.average_readiness}%",
        "",
        "## Matrix",
        "",
        "| Requirement ID | Requirement | Status | Score | Pattern | Wizard | Docs | Training | Troubleshooting | E2E | Gaps |",
        "| --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in item_list:
        gaps = "<br>".join(item.gaps) if item.gaps else "-"
        docs = "<br>".join(item.docs_links) if item.docs_links else "-"
        training = "<br>".join(item.training_example_ids) if item.training_example_ids else "-"
        troubleshooting = "<br>".join(item.troubleshooting_links) if item.troubleshooting_links else "-"
        lines.append(
            "| `{requirement_id}` | {title} | `{status}` | {score} | `{pattern}` | {wizard} | {docs} | {training} | {troubleshooting} | `{e2e}` | {gaps} |".format(
                requirement_id=item.requirement_id,
                title=item.title.get("ru") or item.requirement_id,
                status=item.status,
                score=item.readiness_score,
                pattern=item.recommended_pattern or "-",
                wizard=item.wizard_route or item.workbench_route or "-",
                docs=docs,
                training=training,
                troubleshooting=troubleshooting,
                e2e=item.statuses.e2e,
                gaps=gaps,
            )
        )
    lines.extend([
        "",
        "## Gate Rules",
        "",
        "- `ready` requires wizard/workbench, docs, training, troubleshooting and E2E links.",
        "- `planned` requirements may be visible as `Скоро`, but must not start from `/integration-start`.",
        "- `missing_docs` rows are allowed only when the gap is explicit in this report.",
    ])
    return "\n".join(lines).strip() + "\n"


def validate_coverage(items: list[IntegrationCoverageItem] | None = None) -> tuple[list[str], list[str]]:
    item_list = items or list_static_items()
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for item in item_list:
        if item.requirement_id in seen:
            errors.append(f"Duplicate requirement_id: {item.requirement_id}")
        seen.add(item.requirement_id)
        if not 0 <= item.readiness_score <= 100:
            errors.append(f"{item.requirement_id}: readiness_score out of range")
        _validate_pattern(item, errors, warnings)
        if item.status == "ready":
            _require(item, item.wizard_route or item.workbench_route, "ready item has no wizard/workbench route", errors)
            _require(item, item.docs_links, "ready item has no docs links", errors)
            _require(item, item.training_example_ids, "ready item has no training examples", errors)
            _require(item, item.troubleshooting_links, "ready item has no troubleshooting links", errors)
            _require(item, item.e2e_tests, "ready item has no E2E tests", errors)
        if item.status in {"missing_docs", "missing_wizard"} and not item.gaps:
            errors.append(f"{item.requirement_id}: missing status must have explicit gaps")
        if item.status == "planned" and item.wizard_route:
            errors.append(f"{item.requirement_id}: planned requirement must not expose a startable wizard route")
    if len(item_list) < 11:
        errors.append("Coverage registry must contain at least 11 integration requirements")
    return errors, warnings


def _build_item(definition: dict) -> IntegrationCoverageItem:
    data = deepcopy(definition)
    statuses = CoverageDimensionStatuses(**data["statuses"])
    score = _score(statuses)
    gaps = list(data.get("gaps") or []) + _status_gaps(statuses)
    data["readiness_score"] = score
    data["gaps"] = _dedupe(gaps)
    data["checklist"] = _checklist(data, statuses)
    return IntegrationCoverageItem(**data)


def _score(statuses: CoverageDimensionStatuses) -> int:
    total = 0.0
    for field, weight in WEIGHTS.items():
        status = getattr(statuses, field)
        total += weight * _status_ratio(status)
    return round(total)


def _status_ratio(status: DimensionStatus) -> float:
    if status in {"ready", "not_applicable"}:
        return 1.0
    if status == "partial":
        return PARTIAL_RATIO
    return 0.0


def _status_gaps(statuses: CoverageDimensionStatuses) -> list[str]:
    labels = {
        "wizard": "Мастер/workbench не полностью готов.",
        "docs": "Документация не полностью закрывает сценарий.",
        "training": "Нет полноценного training example.",
        "troubleshooting": "Troubleshooting не полностью привязан к сценарию.",
        "e2e": "Нет полного E2E/pytest покрытия сценария.",
    }
    gaps: list[str] = []
    for field in WEIGHTS:
        status = getattr(statuses, field)
        if status not in {"ready", "not_applicable"}:
            gaps.append(f"{labels[field]} Status: {status}.")
    return gaps


def _checklist(data: dict, statuses: CoverageDimensionStatuses) -> list[CoverageChecklistItem]:
    return [
        CoverageChecklistItem(label="Wizard / workbench", status=statuses.wizard, link=data.get("wizard_route") or data.get("workbench_route")),
        CoverageChecklistItem(label="Docs / recipe", status=statuses.docs, link=(data.get("docs_links") or [None])[0]),
        CoverageChecklistItem(label="Training example", status=statuses.training, link=_training_link(data.get("training_example_ids") or [])),
        CoverageChecklistItem(label="Troubleshooting", status=statuses.troubleshooting, link=(data.get("troubleshooting_links") or [None])[0]),
        CoverageChecklistItem(label="E2E / saved test", status=statuses.e2e, note=", ".join(data.get("e2e_tests") or [])),
    ]


def _training_link(example_ids: list[str]) -> str | None:
    if not example_ids:
        return None
    return f"/training?exampleId={example_ids[0]}"


async def _with_package_statuses(session: AsyncSession, items: list[IntegrationCoverageItem]) -> list[IntegrationCoverageItem]:
    for item in items:
        statuses: list[PackageCoverageStatus] = []
        for package_id in item.package_requirements:
            installed = await package_repository.get_installed(session, package_id)
            warning = None
            if installed is None:
                warning = "Package is not installed"
            elif not installed.enabled:
                warning = "Package is installed but disabled"
            statuses.append(PackageCoverageStatus(package_id=package_id, installed=installed is not None, enabled=bool(installed and installed.enabled), warning=warning))
        item.package_statuses = statuses
    return items


def _validate_pattern(item: IntegrationCoverageItem, errors: list[str], warnings: list[str]) -> None:
    if not item.recommended_pattern:
        return
    try:
        pattern = pattern_service.get_pattern(item.recommended_pattern)
    except Exception as exc:  # noqa: BLE001 - registry validation should report all issues.
        if item.status == "planned":
            warnings.append(f"{item.requirement_id}: planned pattern {item.recommended_pattern} is not registered: {exc}")
        else:
            errors.append(f"{item.requirement_id}: pattern {item.recommended_pattern} is not registered")
        return
    if item.status in ACCEPTABLE_PATTERN_STATUSES and pattern.status != "available":
        errors.append(f"{item.requirement_id}: non-planned requirement references non-startable pattern {item.recommended_pattern}")
    if item.status == "planned" and pattern.status == "available" and item.statuses.wizard != "planned":
        warnings.append(f"{item.requirement_id}: planned requirement references available pattern {item.recommended_pattern}")


def _require(item: IntegrationCoverageItem, value: object, message: str, errors: list[str]) -> None:
    if not value:
        errors.append(f"{item.requirement_id}: {message}")


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
