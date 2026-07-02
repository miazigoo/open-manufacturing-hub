from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["mock-1c"])


@router.get("/api/mock-onec/hs/omh/health")
async def mock_onec_health():
    return {"success": True, "status": "ok", "service": "mock-1c-http-service"}


@router.post("/api/mock-onec/hs/omh/shipment-facts")
async def mock_onec_shipment_facts(body: dict[str, Any]):
    order_id = _external_order_id(body)
    if order_id == "404":
        return {"success": False, "error_code": "ORDER_NOT_FOUND", "error_message": "Order 404 was not found in 1C"}
    if order_id == "500":
        return JSONResponse(status_code=500, content={"error": "Internal 1C error"})
    return {
        "success": True,
        "external_document_id": f"1C-SHIP-{order_id or 'UNKNOWN'}",
        "status": "accepted",
        "message": "Shipment fact accepted",
    }


@router.post("/api/mock-onec/hs/omh/stock-balances")
async def mock_onec_stock_balances(body: dict[str, Any]):
    return {"success": True, "external_document_id": "1C-STOCK-BALANCE", "status": "accepted", "message": "Stock balance accepted", "echo": body.get("payload", {})}


def _external_order_id(body: dict[str, Any]) -> str | None:
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else body
    value = payload.get("external_order_id") if isinstance(payload, dict) else None
    return str(value) if value is not None else None
