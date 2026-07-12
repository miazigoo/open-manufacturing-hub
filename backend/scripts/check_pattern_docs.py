#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.integration_patterns import certification  # noqa: E402
from app.packages_training.examples import TRAINING_EXAMPLES  # noqa: E402


def main() -> int:
    response = certification.list_certifications()
    errors, warnings = certification.validate_certifications(response.items)
    errors.extend(validate_training_examples(response.items))
    errors.extend(validate_docs_routes(response.items))

    summary = response.summary
    print("Pattern docs certification check")
    print(
        "patterns={total} ready_for_training={ready} partial={partial} not_started={not_started} problems={problems}".format(
            total=summary.total,
            ready=summary.ready_for_training,
            partial=summary.partial,
            not_started=summary.not_started,
            problems=summary.problem_patterns,
        )
    )
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


def validate_training_examples(items) -> list[str]:
    errors: list[str] = []
    for item in items:
        if item.certification_status not in {"ready_for_training", "ready_for_production"}:
            continue
        training_links = [check.link for check in item.checks if check.key == "training_example" and check.link]
        if not training_links:
            errors.append(f"{item.pattern_id}: ready pattern has no training link")
            continue
        for link in training_links:
            example_id = link.split("exampleId=", 1)[-1]
            if example_id not in TRAINING_EXAMPLES:
                errors.append(f"{item.pattern_id}: training example does not exist: {example_id}")
    return errors


def validate_docs_routes(items) -> list[str]:
    docs_dir = REPO_ROOT / "frontend" / "src" / "features" / "docs"
    source = "\n".join(path.read_text(encoding="utf-8") for path in docs_dir.glob("*.ts"))
    errors: list[str] = []
    for item in items:
        links = [item.docs_link, *[check.link for check in item.checks if check.key == "troubleshooting"]]
        for route in links:
            if route and route.startswith("/docs/") and not docs_route_appears(route, source):
                errors.append(f"{item.pattern_id}: docs route is not registered in frontend docs: {route}")
    return errors


def docs_route_appears(route: str, source: str) -> bool:
    parts = route.strip("/").split("/")
    if len(parts) == 3 and parts[0] == "docs" and parts[1] == "core":
        return parts[2] in source
    if len(parts) < 4 or parts[0] != "docs":
        return True
    package_id, section_id, slug = parts[1], parts[2], parts[3]
    if slug not in source or section_id not in source:
        return False
    if package_id == "core":
        return "id: 'core'" in source or 'id: "core"' in source
    if package_id == "onec":
        return "onecPackageSeed" in source
    if package_id == "printer":
        return "id: 'printer'" in source or 'id: "printer"' in source
    return package_id in source


if __name__ == "__main__":
    raise SystemExit(main())
