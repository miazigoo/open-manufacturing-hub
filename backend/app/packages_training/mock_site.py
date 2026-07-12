from __future__ import annotations

import re
from typing import Any


def import_order_to_site(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    order = payload.get("order") if isinstance(payload.get("order"), dict) else {}
    order_number = str(order.get("number") or payload.get("order_number") or "").strip()
    site_code = str(payload.get("site_code") or "").strip()
    if site_code == "ERROR":
        return 400, {
            "success": False,
            "error_code": "SITE_REJECTED_ORDER",
            "error_message": "Training site rejected order",
        }
    if not order_number:
        return 422, {
            "success": False,
            "error_code": "ORDER_NUMBER_REQUIRED",
            "error_message": "order.number or order_number is required.",
        }
    external_id = "SITE-ORDER-260666-6938" if order_number == "260666/6938" else f"SITE-ORDER-{_safe_token(order_number)}"
    return 200, {
        "success": True,
        "external_id": external_id,
        "status": "accepted",
        "order_number": order_number,
    }


def _safe_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return token or "UNKNOWN"
