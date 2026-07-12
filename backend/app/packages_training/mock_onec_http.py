from __future__ import annotations

from typing import Any
import xml.etree.ElementTree as ET


def save_order_external_id(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    external_id = str(payload.get("external_id") or "").strip()
    if external_id == "ERROR":
        return 500, {
            "success": False,
            "error": "ONEC_WRITEBACK_FAILED",
            "message": "Training 1C writeback failed by design.",
        }
    if not external_id:
        return 422, {
            "success": False,
            "error": "EXTERNAL_ID_REQUIRED",
            "message": "external_id is required.",
        }
    return 200, {"success": True, "message": "External id saved"}


def accept_shipment_fact(payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    body = payload.get("payload") if isinstance(payload.get("payload"), dict) else payload
    order_number = str(body.get("order_number") or "").strip()
    wms_shipment_id = str(body.get("wms_shipment_id") or "").strip()
    items = body.get("items")
    if order_number == "404":
        return 200, {
            "success": False,
            "error_code": "ORDER_NOT_FOUND",
            "error_message": "Заказ 404 не найден в 1С",
        }
    if not isinstance(items, list) or not items:
        return 422, {
            "success": False,
            "error_code": "ITEMS_REQUIRED",
            "error_message": "items must be a non-empty array.",
        }
    if not wms_shipment_id:
        return 422, {
            "success": False,
            "error_code": "WMS_SHIPMENT_ID_REQUIRED",
            "error_message": "wms_shipment_id is required.",
        }
    return 200, {
        "success": True,
        "external_document_id": f"1C-SHIP-{wms_shipment_id}",
        "status": "accepted",
        "message": "Shipment fact accepted",
    }


def accept_raw_xml(raw_xml: str) -> tuple[int, dict[str, Any]]:
    document_number = _xml_text(raw_xml, "Номер") or _xml_text(raw_xml, "Number")
    if document_number == "ERROR":
        return 422, {
            "success": False,
            "error_code": "XML_DOCUMENT_REJECTED",
            "error_message": "Training 1C rejected XML document ERROR",
            "document_number": document_number,
        }
    return 200, {
        "success": True,
        "message": "XML accepted",
        "document_number": document_number or "unknown",
    }


def _xml_text(raw_xml: str, tag_name: str) -> str | None:
    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return None
    for item in root.iter():
        if item.tag.split("}", 1)[-1] == tag_name:
            value = (item.text or "").strip()
            return value or None
    return None
