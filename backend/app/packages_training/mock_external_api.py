from __future__ import annotations

from typing import Any


def import_order(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    order = payload.get("order") if isinstance(payload.get("order"), dict) else {}
    order_number = str(order.get("number") or payload.get("order_number") or "").strip()
    if order_number == "ERROR-500":
        return 500, {
            "success": False,
            "error": "TRAINING_EXTERNAL_API_ERROR",
            "message": "Training External API returned HTTP 500 by design.",
            "order_number": order_number,
        }
    if not order_number:
        return 422, {
            "success": False,
            "error": "ORDER_NUMBER_REQUIRED",
            "message": "order.number or order_number is required.",
        }
    return 200, {
        "success": True,
        "external_id": "TRAIN-ORDER-001",
        "status": "accepted",
        "order_number": order_number,
    }


def sync_contractor(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    contractor = payload.get("contractor") if isinstance(payload.get("contractor"), dict) else {}
    inn = str(contractor.get("inn") or payload.get("inn") or "").strip()
    if not inn:
        return 422, {
            "success": False,
            "error": "INN_REQUIRED",
            "message": "contractor.inn or inn is required.",
        }
    return 200, {
        "success": True,
        "external_id": "TRAIN-CONTRACTOR-001",
        "status": "synced",
        "inn": inn,
    }
