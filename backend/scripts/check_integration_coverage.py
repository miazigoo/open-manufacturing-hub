#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.integration_coverage import service  # noqa: E402
from app.packages_training.examples import TRAINING_EXAMPLES  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Integration Requirements Coverage registry")
    parser.add_argument("--write-report", action="store_true", help="write docs/reports/integration-coverage-report.md")
    args = parser.parse_args()

    items = service.list_static_items()
    errors, warnings = service.validate_coverage(items)
    errors.extend(validate_training_examples(items))
    errors.extend(validate_docs_routes(items))
    errors.extend(validate_e2e_names(items))

    report = service.build_report(items)
    if args.write_report:
        report_path = REPO_ROOT / "docs" / "reports" / "integration-coverage-report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")

    summary = service.build_summary(items)
    print("Integration coverage check")
    print(f"requirements={summary.total} ready={summary.ready} partial={summary.partial} planned={summary.planned} average={summary.average_readiness}%")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


def validate_training_examples(items) -> list[str]:
    errors: list[str] = []
    for item in items:
        if item.statuses.training == "ready":
            for example_id in item.training_example_ids:
                if example_id not in TRAINING_EXAMPLES:
                    errors.append(f"{item.requirement_id}: training example does not exist: {example_id}")
    return errors


def validate_docs_routes(items) -> list[str]:
    docs_dir = REPO_ROOT / "frontend" / "src" / "features" / "docs"
    source = "\n".join(path.read_text(encoding="utf-8") for path in docs_dir.glob("*.ts"))
    errors: list[str] = []
    for item in items:
        if item.statuses.docs in {"ready", "partial"}:
            for route in item.docs_links:
                if route.startswith("/docs/") and not docs_route_appears(route, source):
                    errors.append(f"{item.requirement_id}: docs route is not registered in frontend docs: {route}")
        if item.statuses.troubleshooting in {"ready", "partial"}:
            for route in item.troubleshooting_links:
                if route.startswith("/docs/") and not docs_route_appears(route, source):
                    errors.append(f"{item.requirement_id}: troubleshooting route is not registered in frontend docs: {route}")
    return errors


def docs_route_appears(route: str, source: str) -> bool:
    parts = route.strip("/").split("/")
    if len(parts) < 4 or parts[0] != "docs":
        return True
    package_id, section_id, slug = parts[1], parts[2], parts[3]
    if slug not in source:
        return False
    if section_id not in source:
        return False
    if package_id == "core":
        return "id: 'core'" in source or 'id: "core"' in source
    if package_id == "onec":
        return "onecPackageSeed" in source
    if package_id == "printer":
        return "id: 'printer'" in source or 'id: "printer"' in source
    return package_id in source


def validate_e2e_names(items) -> list[str]:
    tests_dir = BACKEND_ROOT / "app" / "tests"
    source = "\n".join(path.read_text(encoding="utf-8") for path in tests_dir.glob("test_*.py"))
    errors: list[str] = []
    for item in items:
        if item.statuses.e2e == "ready":
            for test_name in item.e2e_tests:
                if f"def {test_name}" not in source and f"async def {test_name}" not in source:
                    errors.append(f"{item.requirement_id}: e2e test name is not present: {test_name}")
    return errors


if __name__ == "__main__":
    raise SystemExit(main())
