from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

BASE_URL = os.getenv("E2E_BASE_URL", os.getenv("SMOKE_BASE_URL", "http://localhost:8000")).rstrip("/")


class E2EFailure(RuntimeError):
    pass


def request(path: str, method: str = "GET", payload: Any | None = None, headers: dict[str, str] | None = None, raw: bytes | None = None) -> Any:
    data = raw
    request_headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(f"{BASE_URL}{path}", data=data, method=method, headers=request_headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        raise E2EFailure(f"{method} {path} failed: HTTP {exc.code} {body}") from exc
    except urllib.error.URLError as exc:
        raise E2EFailure(f"{method} {path} failed: {exc.reason}") from exc


def ok(label: str) -> None:
    print(f"OK {label}")


def install_package(package_id: str, install_demo_data: bool = False) -> None:
    response = request(f"/api/packages/{package_id}/install", "POST", {"install_demo_data": install_demo_data})
    package = response.get("package") if isinstance(response, dict) else None
    if not package or package.get("enabled") is not True:
        raise E2EFailure(f"package {package_id} was not enabled: {response}")


def require_auth_open() -> None:
    state = request("/api/auth/state")
    if isinstance(state, dict) and state.get("requires_login"):
        raise E2EFailure("Auth package is enabled and UI/API session is required. Run release e2e against a fixture DB without auth, or login-support the runner.")
    ok("auth gate state")


def ensure_release_surface() -> None:
    install_package("omh-package-onec", install_demo_data=True)
    install_package("omh-package-printer", install_demo_data=False)
    request("/api/integration-bus/install-presets", "POST")
    for path in (
        "/api/scenario-library/marking-pool-to-internal-service/install",
        "/api/scenario-library/onec-post-two-odata-to-endpoint/install",
    ):
        request(path, "POST")
    ok("packages and scenario surface")


def assert_timeline_success(event_id: str, label: str, *, allow_waiting: bool = False) -> dict[str, Any]:
    timeline = request(f"/api/events/{event_id}/timeline")
    if not isinstance(timeline, dict):
        raise E2EFailure(f"{label}: timeline is not an object")
    status = ((timeline.get("event") or {}).get("status"))
    if status == "success":
        ok(label)
        return timeline
    queue_status = ((timeline.get("queue_item") or {}).get("status"))
    if allow_waiting and queue_status in {"waiting", "processing", "retry_waiting"}:
        ok(f"{label} queued")
        return timeline
    raise E2EFailure(f"{label}: expected success, got event={status} queue={queue_status}")


def process_queue_until(queue_item_id: str, expected: set[str], label: str, limit: int = 5) -> dict[str, Any]:
    last_item: dict[str, Any] | None = None
    for _ in range(limit):
        request("/api/queue/process-once?worker=release-e2e", "POST")
        item = request(f"/api/queue/{queue_item_id}")
        if isinstance(item, dict):
            last_item = item
            if item.get("status") in expected:
                ok(label)
                return item
    if last_item and last_item.get("event_id"):
        try:
            timeline = request(f"/api/events/{last_item['event_id']}/timeline")
        except Exception as exc:  # best-effort diagnostics
            timeline = {"timeline_error": str(exc)}
        raise E2EFailure(f"{label}: queue item did not reach {sorted(expected)}; last={last_item}; timeline={timeline}")
    raise E2EFailure(f"{label}: queue item did not reach {sorted(expected)}; last={last_item}")


def scenario_marking_pool() -> None:
    body = request(
        "/api/bus/in/marking-pool",
        "POST",
        {"pool_type": "DNP", "order_id": "REL-POOL-001", "codes": ["010464615169738421REL"]},
    )
    if not isinstance(body, dict) or not body.get("event_id") or not body.get("queue_item_id"):
        raise E2EFailure(f"marking-pool response missing ids: {body}")
    process_queue_until(body["queue_item_id"], {"completed"}, "marking-pool queue completed")
    timeline = assert_timeline_success(body["event_id"], "marking-pool timeline")
    runs = timeline.get("runs") or []
    if not runs or not any(step.get("step_name") in {"call_connector", "return_response"} for step in runs[0].get("steps", [])):
        raise E2EFailure("marking-pool timeline has no connector/response step")


def scenario_two_odata_to_endpoint() -> None:
    body = request(
        "/api/bus/in/onec-pool-to-dnp",
        "POST",
        {"inn": "1234567890", "product_code": "ABC-123", "pool_id": "REL-DNP-001", "codes": ["code1", "code2"]},
    )
    if not isinstance(body, dict) or not body.get("event_id"):
        raise E2EFailure(f"onec-pool-to-dnp response missing event_id: {body}")
    if body.get("status") != "completed":
        process_queue_until(body["queue_item_id"], {"completed"}, "two-odata queue completed")
    timeline = assert_timeline_success(body["event_id"], "two-odata timeline")
    text = json.dumps(timeline, ensure_ascii=False)
    for marker in ("Find contractor by INN", "Find product by code", "Build DNP payload"):
        if marker not in text:
            raise E2EFailure(f"two-odata timeline missing marker: {marker}")


def scenario_xml_bridge() -> None:
    install = request("/api/scenario-library/onec_xml_raw_bridge/install", "POST", {"endpoint_slug": "release-e2e-upd-xml"})
    if not isinstance(install, dict) or not install.get("endpoint_url"):
        raise E2EFailure(f"xml scenario install failed: {install}")
    xml = "<Документ><Номер>REL-UPD-001</Номер><Контрагент ИНН=\"1234567890\"/></Документ>".encode("utf-8")
    body = request("/api/bus/in/release-e2e-upd-xml", "POST", raw=xml, headers={"Content-Type": "application/xml"})
    if not isinstance(body, dict) or not body.get("message_id") or not body.get("event_id"):
        raise E2EFailure(f"xml bridge response missing ids: {body}")
    assert_timeline_success(body["event_id"], "xml bridge timeline", allow_waiting=True)


def scenario_queue_and_dlq() -> None:
    created = request(
        "/api/queue",
        "POST",
        {
            "business_object": "ReleaseOrder",
            "business_key": "release-e2e-dlq-001",
            "operation": "force_dlq",
            "payload_json": {"order_id": "release-e2e-dlq-001"},
            "max_attempts": 1,
        },
    )
    if not isinstance(created, dict) or not created.get("id"):
        raise E2EFailure(f"queue create failed: {created}")
    dlq = request(f"/api/queue/{created['id']}/move-to-dlq?{urllib.parse.urlencode({'reason': 'Release e2e printer unavailable'})}", "POST")
    if not isinstance(dlq, dict) or not dlq.get("id"):
        raise E2EFailure(f"move to DLQ failed: {dlq}")
    restored = request(f"/api/dlq/{dlq['id']}/edit-and-retry", "POST", {"payload_json": {"order_id": "release-e2e-dlq-001", "fixed": True}})
    if not isinstance(restored, dict) or restored.get("status") != "waiting":
        raise E2EFailure(f"DLQ edit-and-retry did not restore queue item: {restored}")
    completed = request(f"/api/queue/{restored['id']}/force-complete", "POST")
    if not isinstance(completed, dict) or completed.get("status") != "completed":
        raise E2EFailure(f"queue force-complete failed: {completed}")
    ok("queue DLQ edit retry completed")


def scenario_printer_dry_run() -> None:
    body = request(
        "/api/printing/onec/send-batch",
        "POST",
        {
            "job_key": "release-e2e-print-001",
            "source_system": "1C ERP",
            "source_document_id": "REL-PRINT-001",
            "printer": {"name": "Release E2E Zebra", "host": "127.0.0.1", "port": 9100, "dpi": 203},
            "dry_run": True,
            "lines": [{"sequence_no": 1, "code": "010460123456789021REL", "zpl": "^XA\n^FO0,0\n^FDREL^FS\n^XZ"}],
        },
    )
    if not isinstance(body, dict) or body.get("sent") != 1 or body.get("failed") != 0:
        raise E2EFailure(f"printer dry run failed: {body}")
    ok("printer dry run")


def scenario_doctor_and_inventory() -> None:
    inventory = request("/api/packages/route-inventory")
    if not isinstance(inventory, list) or not any(item.get("path") == "/api/bus/in/{slug}" for item in inventory):
        raise E2EFailure("route inventory does not include core bus route")
    if any(("/api/onec" in item.get("path", "") or "/api/printing" in item.get("path", "")) and not item.get("guarded") for item in inventory):
        raise E2EFailure("route inventory has unguarded package-looking route")
    ok("route inventory")

    doctor = request("/api/production/doctor")
    if not isinstance(doctor, dict) or doctor.get("status") not in {"ok", "warning"}:
        raise E2EFailure(f"doctor failed: {doctor}")
    if not any(item.get("name") == "Package compatibility" for item in doctor.get("checks", [])):
        raise E2EFailure("doctor response missing Package compatibility check")
    ok("production doctor")


def main() -> int:
    require_auth_open()
    ensure_release_surface()
    scenario_marking_pool()
    scenario_two_odata_to_endpoint()
    scenario_xml_bridge()
    scenario_queue_and_dlq()
    scenario_printer_dry_run()
    scenario_doctor_and_inventory()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
