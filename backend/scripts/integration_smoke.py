from __future__ import annotations

import json
import os
import sys
import time
from typing import Any
from urllib.parse import quote
import urllib.error
import urllib.request

BASE_URL = os.getenv("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
TIMEOUT_SECONDS = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "10"))


def request(path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any] | list[Any] | None:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"{method} {path} failed: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc.reason}") from exc


def ok(label: str) -> None:
    print(f"OK {label}")


def require_dict(value: dict[str, Any] | list[Any] | None, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} response must be an object")
    return value


def require_timeline(event_id: str, label: str) -> None:
    timeline = require_dict(request(f"/api/events/{event_id}/timeline"), f"{label} timeline")
    runs = timeline.get("runs")
    if not isinstance(runs, list) or not runs:
        raise RuntimeError(f"{label} timeline did not include runs")
    first_run = runs[0]
    if not isinstance(first_run, dict) or not isinstance(first_run.get("steps"), list):
        raise RuntimeError(f"{label} timeline did not include step evidence")


def main() -> int:
    suffix = str(int(time.time()))
    connector_id: str | None = None
    connector_name = f"Integration Smoke Webhook {suffix}"

    try:
        health = require_dict(request("/api/health"), "health")
        if health.get("status") != "ok":
            raise RuntimeError("health endpoint did not return ok")
        ok("backend health")

        connector_types = request("/api/connectors/types")
        if not isinstance(connector_types, list):
            raise RuntimeError("connector types response must be a list")
        type_names = {item.get("connector_type") for item in connector_types if isinstance(item, dict)}
        missing_types = {"webhook", "rest"} - type_names
        if missing_types:
            raise RuntimeError(f"missing connector types: {sorted(missing_types)}")
        ok("connector types")

        connector = require_dict(
            request(
                "/api/connectors",
                "POST",
                {
                    "name": connector_name,
                    "connector_type": "webhook",
                    "direction": "source",
                    "enabled": True,
                    "config_json": {
                        "default_source_system": "External Portal",
                        "default_target_system": "Mock WMS",
                        "event_type_field": "event_type",
                        "entity_type_field": "entity_type",
                        "entity_id_field": "entity_id",
                    },
                },
            ),
            "create webhook connector",
        )
        connector_id = str(connector.get("id") or "")
        if not connector_id:
            raise RuntimeError("create webhook connector response did not include id")
        ok("create webhook connector")

        webhook_event = require_dict(
            request(
                f"/api/webhooks/{quote(connector_name, safe='')}",
                "POST",
                {
                    "correlation_id": f"integration-smoke-webhook-{suffix}",
                    "target_system": "Mock WMS",
                    "event_type": "SalesOrderCreated",
                    "entity_type": "SalesOrder",
                    "entity_id": f"INT-WEBHOOK-{suffix}",
                    "payload": {
                        "order_id": f"INT-WEBHOOK-{suffix}",
                        "warehouse_id": "MAIN",
                        "items": [{"sku": "SMOKE", "qty": 1, "uom": "pcs"}],
                    },
                },
            ),
            "webhook event",
        )
        webhook_event_id = str(webhook_event.get("event_id") or "")
        if not webhook_event_id:
            raise RuntimeError("webhook response did not include event_id")
        ok("webhook event")

        require_timeline(webhook_event_id, "webhook event")
        ok("webhook timeline")

        direct_event = require_dict(
            request(
                "/api/events",
                "POST",
                {
                    "correlation_id": f"integration-smoke-direct-{suffix}",
                    "source_system": "Integration Smoke",
                    "target_system": "Mock WMS",
                    "event_type": "SalesOrderCreated",
                    "entity_type": "SalesOrder",
                    "entity_id": f"INT-DIRECT-{suffix}",
                    "payload": {
                        "order_id": f"INT-DIRECT-{suffix}",
                        "warehouse_id": "MAIN",
                        "items": [{"sku": "SMOKE", "qty": 1, "uom": "pcs"}],
                    },
                },
            ),
            "direct event",
        )
        direct_event_id = str(direct_event.get("id") or "")
        if not direct_event_id:
            raise RuntimeError("direct event response did not include id")
        ok("direct event")

        require_timeline(direct_event_id, "direct event")
        ok("direct timeline")

        heartbeat = require_dict(
            request(
                "/api/health/agent-heartbeat",
                "POST",
                {
                    "site_name": "Integration Smoke Site",
                    "site_code": "INT-SMOKE",
                    "agent_name": "integration-smoke-agent",
                    "internet_ok": True,
                    "can_reach_hub": True,
                    "can_reach_wms": True,
                    "can_reach_erp": True,
                    "local_ip": "127.0.0.1",
                    "details_json": {"source": "integration_smoke", "suffix": suffix},
                },
            ),
            "health heartbeat",
        )
        if not heartbeat.get("id"):
            raise RuntimeError("heartbeat response did not include id")
        ok("health heartbeat")

        dashboard = require_dict(request("/api/health/dashboard"), "health dashboard")
        if "sites" not in dashboard:
            raise RuntimeError("health dashboard did not include sites")
        ok("health dashboard")
        return 0
    finally:
        if connector_id:
            try:
                request(f"/api/connectors/{connector_id}", "DELETE")
                ok("cleanup webhook connector")
            except Exception as exc:
                print(f"WARN cleanup webhook connector failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
