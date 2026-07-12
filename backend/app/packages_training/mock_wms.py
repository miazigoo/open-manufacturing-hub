from __future__ import annotations

from typing import Any


def import_orders(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    body = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
    orders = body.get("orders") if isinstance(body, dict) else None
    if orders is None and isinstance(payload.get("orders"), list):
        orders = payload["orders"]
    if not isinstance(orders, list):
        return 422, {
            "success": False,
            "error": "ORDERS_ARRAY_REQUIRED",
            "message": "payload.orders array is required.",
        }
    return 200, {
        "success": True,
        "accepted_count": len(orders),
        "status": "accepted",
    }
