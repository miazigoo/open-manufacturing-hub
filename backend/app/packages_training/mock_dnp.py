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
    field_errors = _validate_marking_pool_payload(payload)
    if field_errors:
        return 422, {
            "success": False,
            "error": "DNP_CONTRACT_VALIDATION_FAILED",
            "message": "Training DNP payload does not match the marking pool contract.",
            "field_errors": field_errors,
            "hint": "Send pool_id, order_id, codes, contractor/inn and product/product_code fields.",
        }
    return 200, {
        "success": True,
        "pool_id": pool_id,
        "order_id": payload.get("order_id"),
        "accepted_codes": len(payload.get("codes") or []),
        "dnp_request_id": "DNP-TRAINING-0001",
        "status": "accepted",
    }


def submit_chz_codes(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    body = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
    order_name = str(body.get("order_name") or body.get("entity_id") or "").strip()
    rows = body.get("rows")
    if order_name == "ERROR-500":
        return 500, {
            "ok": False,
            "error": "DNP_CHZ_IMPORT_FAILED",
            "message": "Training DnP CHZ endpoint returned HTTP 500 by design.",
            "order_name": order_name,
        }
    if not isinstance(rows, list) or not rows:
        return 422, {
            "ok": False,
            "error": "DNP_CHZ_ROWS_REQUIRED",
            "message": "payload.rows must be a non-empty array.",
        }
    return 200, {
        "ok": True,
        "errors": [],
        "rows_count": len(rows),
        "errors_count": 0,
        "order_name": order_name,
        "dnp_request_id": "DNP-CHZ-TRAINING-0001",
    }


def _validate_marking_pool_payload(payload: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}
    if not str(payload.get("pool_id") or payload.get("pool") or "").strip():
        errors["pool_id"] = "required"
    if not str(payload.get("order_id") or "").strip():
        errors["order_id"] = "required"
    codes = payload.get("codes")
    if not isinstance(codes, list) or not codes:
        errors["codes"] = "non_empty_array_required"
    elif any(not str(code or "").strip() for code in codes):
        errors["codes"] = "all_codes_must_be_non_empty"

    contractor = payload.get("contractor") if isinstance(payload.get("contractor"), dict) else {}
    if not str(contractor.get("inn") or payload.get("inn") or "").strip():
        errors["contractor.inn"] = "required"

    product = payload.get("product") if isinstance(payload.get("product"), dict) else {}
    if not str(product.get("gtin") or payload.get("product_code") or "").strip():
        errors["product.gtin"] = "required"
    return errors
