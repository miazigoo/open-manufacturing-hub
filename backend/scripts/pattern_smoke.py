#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.integration_patterns import certification  # noqa: E402
from app.packages_training.examples import TRAINING_EXAMPLES  # noqa: E402

SMOKE_PATTERNS = [
    "request_odata_response",
    "request_odata_send_endpoint",
    "request_multiple_odata_response",
    "xml_raw_bridge",
    "xml_odata_xml_response",
    "request_print",
    "wms_fact_to_onec",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-check certified integration patterns")
    parser.add_argument("--pattern", action="append", dest="patterns", help="pattern_id to smoke; can be passed multiple times")
    args = parser.parse_args()

    pattern_ids = args.patterns or SMOKE_PATTERNS
    errors: list[str] = []
    smoked_training_examples: list[str] = []
    print("Pattern smoke")
    for pattern_id in pattern_ids:
        item = certification.get_certification(pattern_id)
        if item.certification_status in {"not_started", "deprecated"}:
            errors.append(f"{pattern_id}: not startable certification status {item.certification_status}")
        if not item.wizard_route:
            errors.append(f"{pattern_id}: wizard_route is missing")
        if not item.docs_link:
            errors.append(f"{pattern_id}: docs_link is missing")
        training_check = next((check for check in item.checks if check.key == "training_example"), None)
        if training_check and training_check.link:
            example_id = training_check.link.split("exampleId=", 1)[-1]
            if example_id in TRAINING_EXAMPLES:
                smoked_training_examples.append(example_id)
        print(f"- {pattern_id}: {item.certification_status} route={item.wizard_route} docs={item.docs_link}")

    if not smoked_training_examples:
        errors.append("no training example was available for smoke")
    else:
        print(f"training_examples={','.join(sorted(set(smoked_training_examples)))}")

    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
