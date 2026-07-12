from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.integration_patterns import certification


async def test_pattern_certification_list_summary_and_ready_pattern(client):
    response = await client.get("/api/integration-patterns/certification")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["summary"]["total"] >= 11
    assert body["summary"]["ready_for_training"] >= 5
    assert body["summary"]["partial"] >= 1

    by_id = {item["pattern_id"]: item for item in body["items"]}
    assert "request_odata_response" in by_id
    ready = by_id["request_odata_response"]
    assert ready["certification_status"] == "ready_for_training"
    assert ready["ui_status"] == "passed"
    assert ready["docs_status"] == "passed"
    assert ready["training_status"] == "passed"
    assert ready["tests_status"] == "passed"
    assert ready["simple_mode_status"] == "passed"
    assert ready["docs_link"] == "/docs/onec/recipes/external-service-lookup-contractor"
    assert ready["coverage_requirement_ids"] == ["external_api_asks_1c_by_inn"]


async def test_pattern_certification_detail_check_and_partial_training_gap(client):
    detail = await client.get("/api/integration-patterns/source_web_api_writeback_onec/certification")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["certification_status"] == "partial"
    assert body["training_status"] == "warning"
    assert any("training" in problem.lower() for problem in body["problems"])
    assert body["wizard_route"] == "/master?pattern=source_web_api_writeback_onec"

    check = await client.post("/api/integration-patterns/source_web_api_writeback_onec/certification/check")
    assert check.status_code == 200, check.text
    assert check.json()["certification_status"] == body["certification_status"]


async def test_pattern_certification_unknown_and_uncertified_patterns_are_404(client):
    unknown = await client.get("/api/integration-patterns/nope/certification")
    assert unknown.status_code == 404

    registered_but_not_certified = await client.get("/api/integration-patterns/request_response/certification")
    assert registered_but_not_certified.status_code == 404


def test_pattern_certification_missing_docs_check_can_fail():
    item = certification.certify_pattern("request_odata_response")
    item.docs_link = None
    errors, warnings = certification.validate_certifications([item])
    assert any("docs_link is missing" in error for error in errors)
    assert warnings == []


def test_pattern_docs_and_smoke_scripts_pass():
    backend_root = Path(__file__).resolve().parents[2]
    for script in ["scripts/check_pattern_docs.py", "scripts/pattern_smoke.py", "scripts/check_simple_mode_ux.py"]:
        result = subprocess.run(
            [sys.executable, script],
            cwd=backend_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert result.returncode == 0, result.stdout
