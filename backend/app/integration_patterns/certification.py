from __future__ import annotations

from collections import Counter
from typing import Iterable

from app.core.errors import NotFoundError
from app.integration_coverage import service as coverage_service
from app.integration_coverage.schemas import DimensionStatus, IntegrationCoverageItem
from app.integration_patterns import service as pattern_service
from app.integration_patterns.schemas import (
    IntegrationPattern,
    LocalizedText,
    PatternCertification,
    PatternCertificationCheck,
    PatternCertificationCheckStatus,
    PatternCertificationListResponse,
    PatternCertificationStatus,
    PatternCertificationSummary,
)

CERTIFIED_PATTERN_IDS = [
    "request_odata_response",
    "request_odata_send_endpoint",
    "request_odata_object_foreach_send_endpoint",
    "source_web_api_writeback_onec",
    "request_multiple_odata_response",
    "wms_fact_to_onec",
    "xml_raw_bridge",
    "xml_odata_xml_response",
    "request_print",
    "poll_odata_send_target",
    "request_save_file_optional_forward",
]

PATTERN_ENDPOINT_SLUGS = {
    "request_odata_response": "request-odata-response",
    "request_odata_send_endpoint": "request-odata-send-endpoint",
    "request_odata_object_foreach_send_endpoint": "request-odata-object-foreach-send-endpoint",
    "request_multiple_odata_response": "request-multiple-odata-response",
    "wms_fact_to_onec": "wms-fact-to-onec",
    "xml_raw_bridge": "xml-raw-bridge",
    "xml_odata_xml_response": "xml-odata-xml-response",
    "request_print": "request-print",
    "poll_odata_send_target": "poll-odata-send-target",
    "source_web_api_writeback_onec": "source-web-api-writeback-onec",
}

WORKBENCH_PATTERNS = {"request_save_file_optional_forward"}
TRAINING_READY = {"ready", "partial"}
PASSING_DIMENSIONS = {"ready", "not_applicable"}
WARNING_DIMENSIONS = {"partial", "missing_training", "missing_docs", "missing_wizard", "missing"}

STATUS_LABELS: dict[PatternCertificationStatus, LocalizedText] = {
    "ready_for_production": {"ru": "Готово", "en": "Ready"},
    "ready_for_training": {"ru": "Учебный пример есть", "en": "Training-ready"},
    "partial": {"ru": "Частично", "en": "Partial"},
    "not_started": {"ru": "Запланировано", "en": "Planned"},
    "deprecated": {"ru": "Deprecated", "en": "Deprecated"},
}


def list_certifications() -> PatternCertificationListResponse:
    items = [certify_pattern(pattern_id) for pattern_id in CERTIFIED_PATTERN_IDS]
    return PatternCertificationListResponse(summary=build_summary(items), items=items)


def get_certification(pattern_id: str) -> PatternCertification:
    if pattern_id not in CERTIFIED_PATTERN_IDS:
        try:
            pattern_service.get_pattern(pattern_id)
        except Exception as exc:  # noqa: BLE001 - keep API error stable.
            raise NotFoundError("Integration pattern certification not found") from exc
        raise NotFoundError("Integration pattern is not certified yet")
    return certify_pattern(pattern_id)


def check_certification(pattern_id: str) -> PatternCertification:
    return get_certification(pattern_id)


def build_summary(items: Iterable[PatternCertification]) -> PatternCertificationSummary:
    item_list = list(items)
    counts = Counter(item.certification_status for item in item_list)
    return PatternCertificationSummary(
        total=len(item_list),
        not_started=counts.get("not_started", 0),
        partial=counts.get("partial", 0),
        ready_for_training=counts.get("ready_for_training", 0),
        ready_for_production=counts.get("ready_for_production", 0),
        deprecated=counts.get("deprecated", 0),
        problem_patterns=sum(1 for item in item_list if item.problems),
    )


def certify_pattern(pattern_id: str) -> PatternCertification:
    pattern = pattern_service.get_pattern(pattern_id)
    coverage_items = coverage_for_pattern(pattern_id)
    checks = build_checks(pattern, coverage_items)
    certification_status = resolve_status(pattern, coverage_items, checks)
    problems = [localize(check.message) for check in checks if check.status in {"failed", "warning", "planned"}]
    actions = build_actions(pattern, coverage_items, checks, certification_status)
    return PatternCertification(
        pattern_id=pattern.pattern_id,
        title=pattern.title,
        description=pattern.description,
        certification_status=certification_status,
        status_label=STATUS_LABELS[certification_status],
        wizard_route=pattern.wizard_route,
        docs_link=pattern.docs_link,
        coverage_requirement_ids=[item.requirement_id for item in coverage_items],
        ui_status=rollup(checks, {"integration_start_card", "wizard_route", "preview", "save_disabled", "run_test"}),
        docs_status=rollup(checks, {"docs_link", "troubleshooting"}),
        training_status=rollup(checks, {"training_example"}),
        tests_status=rollup(checks, {"e2e_tests"}),
        timeline_status=rollup(checks, {"timeline"}),
        simple_mode_status=rollup(checks, {"simple_mode"}),
        checks=checks,
        problems=problems,
        actions=actions,
    )


def coverage_for_pattern(pattern_id: str) -> list[IntegrationCoverageItem]:
    return [item for item in coverage_service.list_static_items() if item.recommended_pattern == pattern_id]


def build_checks(pattern: IntegrationPattern, coverage_items: list[IntegrationCoverageItem]) -> list[PatternCertificationCheck]:
    primary = coverage_items[0] if coverage_items else None
    endpoint_slug = PATTERN_ENDPOINT_SLUGS.get(pattern.pattern_id)
    is_workbench = pattern.pattern_id in WORKBENCH_PATTERNS
    return [
        check(
            "integration_start_card",
            "Карточка в Scenario Router",
            "Integration Start card",
            "passed" if any(item.show_in_integration_start for item in coverage_items) else "warning",
            "Сценарий виден на /integration-start." if any(item.show_in_integration_start for item in coverage_items) else "Нет карточки /integration-start для этого паттерна.",
            "Scenario is visible on /integration-start." if any(item.show_in_integration_start for item in coverage_items) else "No /integration-start card is mapped to this pattern.",
            "/integration-start",
            "integration_coverage",
        ),
        check(
            "wizard_route",
            "Маршрут мастера/workbench",
            "Wizard or workbench route",
            "passed" if pattern.wizard_route else planned_or_failed(pattern),
            f"Открывается {pattern.wizard_route}." if pattern.wizard_route else "wizard_route не задан.",
            f"Opens {pattern.wizard_route}." if pattern.wizard_route else "wizard_route is missing.",
            pattern.wizard_route,
        ),
        check(
            "preview",
            "Preview до записи",
            "Preview before write",
            "passed" if endpoint_slug or is_workbench else "warning",
            "Есть preview endpoint или production workbench preview." if endpoint_slug or is_workbench else "Нужно выделить preview до записи.",
            "Preview endpoint or workbench preview exists." if endpoint_slug or is_workbench else "A write-free preview should be exposed.",
        ),
        check(
            "save_disabled",
            "Сохранение без production enable",
            "Save without production enable",
            "passed" if endpoint_slug or is_workbench else "warning",
            "Создание оставляет интеграцию disabled или требует явного действия оператора." if endpoint_slug or is_workbench else "Нужно зафиксировать правило disabled-by-default.",
            "Create keeps production disabled or requires an explicit operator action." if endpoint_slug or is_workbench else "Disabled-by-default behavior must be documented.",
        ),
        check(
            "run_test",
            "Тестовый запуск",
            "Test run",
            "passed" if endpoint_slug or is_workbench else "warning",
            "Есть run-test/manual test path." if endpoint_slug or is_workbench else "Нужно добавить run-test/manual test path.",
            "run-test/manual test path exists." if endpoint_slug or is_workbench else "run-test/manual test path is missing.",
        ),
        check(
            "docs_link",
            "Документация",
            "Documentation",
            status_from_dimension(primary.statuses.docs if primary else None, required=bool(pattern.docs_link)),
            "docs_link и recipe присутствуют." if pattern.docs_link else "docs_link отсутствует.",
            "docs_link and recipe are present." if pattern.docs_link else "docs_link is missing.",
            pattern.docs_link,
            "integration_coverage",
        ),
        check(
            "training_example",
            "Training example",
            "Training example",
            training_status(pattern, coverage_items),
            training_message(pattern, coverage_items, "ru"),
            training_message(pattern, coverage_items, "en"),
            training_link(coverage_items),
            "training_sandbox",
        ),
        check(
            "troubleshooting",
            "Troubleshooting",
            "Troubleshooting",
            status_from_dimension(primary.statuses.troubleshooting if primary else None, required=False),
            "Troubleshooting playbook привязан." if primary and primary.troubleshooting_links else "Нужна ссылка на troubleshooting.",
            "Troubleshooting playbook is linked." if primary and primary.troubleshooting_links else "Troubleshooting link is missing.",
            primary.troubleshooting_links[0] if primary and primary.troubleshooting_links else None,
            "integration_coverage",
        ),
        check(
            "e2e_tests",
            "Tests",
            "Tests",
            status_from_dimension(primary.statuses.e2e if primary else None, required=False),
            "E2E/pytest имена указаны." if primary and primary.e2e_tests else "Нужно добавить smoke/e2e проверку.",
            "E2E/pytest names are registered." if primary and primary.e2e_tests else "Smoke/e2e coverage is missing.",
            None,
            "integration_coverage",
        ),
        check(
            "timeline",
            "Timeline / run history",
            "Timeline / run history",
            "passed" if pattern.timeline_hint else "warning",
            "Пользователь видит Timeline или run history после теста." if pattern.timeline_hint else "Нужно описать, где смотреть результат запуска.",
            "User can inspect Timeline or run history after a test." if pattern.timeline_hint else "Result inspection path must be documented.",
        ),
        check(
            "simple_mode",
            "Simple Mode не показывает internals",
            "Simple Mode does not expose internals",
            "passed",
            "Проверяется командой make simple-mode-ux-check.",
            "Checked by make simple-mode-ux-check.",
        ),
    ]


def resolve_status(pattern: IntegrationPattern, coverage_items: list[IntegrationCoverageItem], checks: list[PatternCertificationCheck]) -> PatternCertificationStatus:
    if pattern.status == "coming_soon" or any(item.status == "planned" for item in coverage_items):
        return "not_started"
    if any(check.status == "failed" for check in checks):
        return "partial"
    if coverage_items and all(item.status == "ready" for item in coverage_items):
        return "ready_for_training"
    return "partial"


def rollup(checks: list[PatternCertificationCheck], keys: set[str]) -> PatternCertificationCheckStatus:
    selected = [check.status for check in checks if check.key in keys]
    if not selected:
        return "warning"
    if "failed" in selected:
        return "failed"
    if "planned" in selected:
        return "planned"
    if "warning" in selected:
        return "warning"
    return "passed"


def status_from_dimension(status: DimensionStatus | None, *, required: bool) -> PatternCertificationCheckStatus:
    if status is None:
        return "passed" if required else "warning"
    if status == "planned":
        return "planned"
    if status in PASSING_DIMENSIONS:
        return "passed"
    if status in WARNING_DIMENSIONS:
        return "warning"
    return "failed"


def training_status(pattern: IntegrationPattern, coverage_items: list[IntegrationCoverageItem]) -> PatternCertificationCheckStatus:
    primary = coverage_items[0] if coverage_items else None
    if primary and primary.statuses.training in PASSING_DIMENSIONS:
        return "passed"
    if any(example.startswith("training.") for example in pattern.examples):
        return "passed"
    if primary and primary.statuses.training in TRAINING_READY:
        return "warning"
    return "warning"


def training_message(pattern: IntegrationPattern, coverage_items: list[IntegrationCoverageItem], language: str) -> str:
    primary = coverage_items[0] if coverage_items else None
    has_training = bool(primary and primary.training_example_ids) or any(example.startswith("training.") for example in pattern.examples)
    if language == "ru":
        return "Training example привязан." if has_training else "Нужен training example перед статусом production-ready."
    return "Training example is linked." if has_training else "A training example is required before production-ready status."


def training_link(coverage_items: list[IntegrationCoverageItem]) -> str | None:
    for item in coverage_items:
        if item.training_example_ids:
            return f"/training?exampleId={item.training_example_ids[0]}"
    return None


def planned_or_failed(pattern: IntegrationPattern) -> PatternCertificationCheckStatus:
    return "planned" if pattern.status == "coming_soon" else "failed"


def check(
    key: str,
    ru_label: str,
    en_label: str,
    status: PatternCertificationCheckStatus,
    ru_message: str,
    en_message: str,
    link: str | None = None,
    source: str = "pattern_certification",
) -> PatternCertificationCheck:
    return PatternCertificationCheck(
        key=key,
        label={"ru": ru_label, "en": en_label},
        status=status,
        message={"ru": ru_message, "en": en_message},
        link=link,
        source=source,
    )


def build_actions(
    pattern: IntegrationPattern,
    coverage_items: list[IntegrationCoverageItem],
    checks: list[PatternCertificationCheck],
    status: PatternCertificationStatus,
) -> list[LocalizedText]:
    actions: list[LocalizedText] = []
    if status == "ready_for_training":
        actions.append({"ru": "Прогнать training example и открыть Timeline.", "en": "Run the training example and inspect Timeline."})
    if status == "ready_for_production":
        actions.append({"ru": "Разрешить production enable после smoke run.", "en": "Allow production enable after smoke run."})
    if not coverage_items:
        actions.append({"ru": "Добавить строку в Integration Coverage Matrix.", "en": "Add an Integration Coverage Matrix row."})
    if any(check.key == "training_example" and check.status != "passed" for check in checks):
        actions.append({"ru": "Добавить training sandbox example.", "en": "Add a training sandbox example."})
    if any(check.key == "troubleshooting" and check.status != "passed" for check in checks):
        actions.append({"ru": "Привязать troubleshooting playbook.", "en": "Link a troubleshooting playbook."})
    if any(check.key == "e2e_tests" and check.status != "passed" for check in checks):
        actions.append({"ru": "Добавить smoke/e2e тесты паттерна.", "en": "Add pattern smoke/e2e tests."})
    if not pattern.docs_link:
        actions.append({"ru": "Заполнить docs_link в registry.", "en": "Fill docs_link in the registry."})
    if not actions:
        actions.append({"ru": "Поддерживать checklist при каждом изменении wizard-а.", "en": "Keep this checklist current on every wizard change."})
    return actions


def localize(value: LocalizedText) -> str:
    return value.get("ru") or value.get("en") or ""


def validate_certifications(items: list[PatternCertification] | None = None) -> tuple[list[str], list[str]]:
    item_list = items or list_certifications().items
    errors: list[str] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for item in item_list:
        if item.pattern_id in seen:
            errors.append(f"duplicate certification pattern_id: {item.pattern_id}")
        seen.add(item.pattern_id)
        if not item.docs_link:
            errors.append(f"{item.pattern_id}: docs_link is missing")
        if not item.wizard_route:
            errors.append(f"{item.pattern_id}: wizard_route is missing")
        if not item.coverage_requirement_ids:
            warnings.append(f"{item.pattern_id}: no Integration Coverage Matrix row")
        if item.certification_status in {"ready_for_training", "ready_for_production"}:
            for check_item in item.checks:
                if check_item.key in {"training_example", "troubleshooting", "e2e_tests", "docs_link", "wizard_route"} and check_item.status != "passed":
                    errors.append(f"{item.pattern_id}: ready pattern has non-passing {check_item.key}: {check_item.status}")
        if item.certification_status == "not_started":
            warnings.append(f"{item.pattern_id}: planned/not_started pattern is tracked but not startable")
    missing = sorted(set(CERTIFIED_PATTERN_IDS) - seen)
    for pattern_id in missing:
        errors.append(f"missing certification pattern: {pattern_id}")
    return errors, warnings
