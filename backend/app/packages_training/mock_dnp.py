from __future__ import annotations

from typing import Any


def submit_marking_pool(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    pool_id = str(payload.get("pool_id") or payload.get("pool") or "")
    if pool_id == "POOL-ERROR":
        return 400, {
            "success": False,
            "error": "DNP_POOL_REJECTED",
            "message": "Training DNP rejected this pool by design.",
            "hint": "Use POOL-001 for the happy path or inspect the timeline to see external error handling.",
        }
    return 200, {
        "success": True,
        "pool_id": pool_id or "POOL-001",
        "dnp_request_id": "DNP-TRAINING-0001",
        "status": "accepted",
    }

