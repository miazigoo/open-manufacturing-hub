import hashlib
from typing import Any

from fastapi import APIRouter, Request
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


@router.post("/api/mock-onec/hs/omh/inventory-results")
async def mock_onec_inventory_results(body: dict[str, Any]):
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
    inventory_id = payload.get("inventory_id") or "UNKNOWN"
    return {"success": True, "external_document_id": f"1C-INV-{inventory_id}", "status": "accepted", "message": "Inventory result accepted", "echo": payload}


@router.post("/api/mock-onec/hs/omh/movements")
async def mock_onec_movements(body: dict[str, Any]):
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else {}
    movement_id = payload.get("movement_id") or "UNKNOWN"
    return {"success": True, "external_document_id": f"1C-MOV-{movement_id}", "status": "accepted", "message": "Movement fact accepted", "echo": payload}


@router.post("/api/mock-onec/hs/omh/xml/inbound")
async def mock_onec_xml_inbound(request: Request):
    xml = (await request.body()).decode("utf-8")
    if "<Error>ORDER_NOT_FOUND</Error>" in xml:
        return {"success": False, "error_code": "ORDER_NOT_FOUND", "error_message": "Order not found"}
    return {
        "success": True,
        "status": "accepted",
        "message": "XML accepted by mock 1C",
        "sha256": hashlib.sha256(xml.encode("utf-8")).hexdigest(),
    }


def _external_order_id(body: dict[str, Any]) -> str | None:
    payload = body.get("payload") if isinstance(body.get("payload"), dict) else body
    value = payload.get("external_order_id") if isinstance(payload, dict) else None
    return str(value) if value is not None else None
