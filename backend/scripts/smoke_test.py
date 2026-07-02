from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://localhost:8000")


def request(path: str, method: str = "GET", payload: dict | None = None) -> dict | list | None:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"{method} {path} failed: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc.reason}") from exc


def ok(label: str) -> None:
    print(f"OK {label}")


def main() -> int:
    checks = [
        ("events", "/api/events"),
        ("health", "/api/health/dashboard"),
        ("incidents", "/api/incidents"),
        ("notifications", "/api/notifications/rules"),
        ("connector types", "/api/connectors/types"),
        ("connectors", "/api/connectors"),
        ("execution steps", "/api/execution/steps"),
        ("mappings", "/api/mappings"),
        ("mapping presets", "/api/mappings/presets"),
        ("workflows", "/api/workflows"),
        ("polling jobs", "/api/polling/jobs"),
        ("1c scenarios", "/api/onec-scenarios/presets"),
        ("maintenance", "/api/maintenance"),
        ("retention", "/api/retention/preview"),
    ]
    for label, path in checks:
        request(path)
        ok(label)

    event = request(
        "/api/events",
        "POST",
        {
            "correlation_id": "smoke_test_event",
            "source_system": "Smoke ERP",
            "target_system": "Smoke WMS",
            "event_type": "SalesOrderCreated",
            "entity_type": "SalesOrder",
            "entity_id": "SMOKE-1",
            "payload": {"order_id": "SMOKE-1", "warehouse_id": "MAIN", "items": [{"sku": "SMOKE", "qty": 1}]},
        },
    )
    if not isinstance(event, dict) or not event.get("id"):
        raise RuntimeError("create event response did not include id")
    ok("create event")

    timeline = request(f"/api/events/{event['id']}/timeline")
    if not isinstance(timeline, dict) or not timeline.get("runs"):
        raise RuntimeError("timeline response did not include runs")
    ok("timeline")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
