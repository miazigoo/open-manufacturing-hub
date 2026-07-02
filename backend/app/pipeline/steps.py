from typing import Any

from app.core.errors import PipelineError


STEP_NAMES = ["receive", "normalize", "validate", "map_to_target", "send_to_target", "handle_response"]


def receive(payload: dict[str, Any]) -> dict[str, Any]:
    return dict(payload)


def normalize(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if "warehouse_id" in normalized:
        normalized["warehouse_id"] = str(normalized["warehouse_id"])
    return normalized


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    required = ["order_id", "warehouse_id", "items"]
    missing = [field for field in required if field not in payload]
    return {"valid": not missing, "missing": missing}


def map_to_target(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_order_id": payload.get("order_id"),
        "warehouse_id": payload.get("warehouse_id"),
        "lines": payload.get("items", []),
    }


def outgoing_request(mapped_payload: dict[str, Any]) -> dict[str, Any]:
    return {"method": "POST", "path": "/shipment", "body": mapped_payload}


def send_to_target(request: dict[str, Any]) -> dict[str, Any]:
    warehouse_id = request.get("body", {}).get("warehouse_id")
    if warehouse_id == "005":
        raise PipelineError("WAREHOUSE_NOT_FOUND", "Warehouse 005 not found")
    return {"status_code": 201, "body": {"accepted": True, "target_id": request.get("body", {}).get("target_order_id")}}


def handle_response(response: dict[str, Any]) -> dict[str, Any]:
    return {"handled": True, "target_status_code": response.get("status_code")}
