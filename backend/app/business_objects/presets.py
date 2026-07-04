from __future__ import annotations

from typing import Any


def field(name: str, type_: str = "string", required: bool = False, description: str | None = None) -> dict[str, Any]:
    return {"name": name, "type": type_, "required": required, "description": description}


BUSINESS_OBJECT_PRESETS: list[dict[str, Any]] = [
    {
        "object_type": "Customer",
        "display_name": "Customer",
        "description": "Legal entity or person buying goods and services.",
        "identity_fields": ["uuid", "inn", "external_id", "code"],
        "fields": [field("uuid"), field("inn"), field("kpp"), field("code"), field("name"), field("external_id")],
    },
    {
        "object_type": "Supplier",
        "display_name": "Supplier",
        "description": "Vendor or counterparty supplying goods and services.",
        "identity_fields": ["uuid", "inn", "external_id", "code"],
        "fields": [field("uuid"), field("inn"), field("kpp"), field("code"), field("name"), field("external_id")],
    },
    {
        "object_type": "Product",
        "display_name": "Product",
        "description": "Canonical product, SKU or nomenclature item.",
        "identity_fields": ["uuid", "article", "barcode", "gtin", "external_id", "code"],
        "fields": [field("uuid"), field("article"), field("barcode"), field("gtin"), field("code"), field("name"), field("uom"), field("external_id")],
    },
    {
        "object_type": "Warehouse",
        "display_name": "Warehouse",
        "description": "Storage warehouse or stock location root.",
        "identity_fields": ["uuid", "code", "name", "external_id"],
        "fields": [field("uuid"), field("code"), field("name"), field("site"), field("external_id")],
    },
    {
        "object_type": "Location",
        "display_name": "Location",
        "description": "Physical bin, zone or operational location.",
        "identity_fields": ["uuid", "code", "barcode", "external_id"],
        "fields": [field("uuid"), field("warehouse_uuid"), field("code"), field("barcode"), field("name"), field("external_id")],
    },
    {
        "object_type": "SalesOrder",
        "display_name": "Sales Order",
        "description": "Customer order or outbound fulfillment document.",
        "identity_fields": ["uuid", "number", "external_id"],
        "fields": [field("uuid"), field("number"), field("date", "datetime"), field("customer_uuid"), field("status"), field("external_id")],
    },
    {
        "object_type": "PurchaseOrder",
        "display_name": "Purchase Order",
        "description": "Supplier order or inbound procurement document.",
        "identity_fields": ["uuid", "number", "external_id"],
        "fields": [field("uuid"), field("number"), field("date", "datetime"), field("supplier_uuid"), field("status"), field("external_id")],
    },
    {
        "object_type": "Shipment",
        "display_name": "Shipment",
        "description": "Planned outbound or inbound shipment.",
        "identity_fields": ["uuid", "number", "external_id"],
        "fields": [field("uuid"), field("number"), field("date", "datetime"), field("warehouse_uuid"), field("status"), field("external_id")],
    },
    {
        "object_type": "ShipmentFact",
        "display_name": "Shipment Fact",
        "description": "Confirmed movement or actual shipment fact.",
        "identity_fields": ["uuid", "number", "external_id"],
        "fields": [field("uuid"), field("number"), field("date", "datetime"), field("shipment_uuid"), field("status"), field("external_id")],
    },
    {
        "object_type": "StockBalance",
        "display_name": "Stock Balance",
        "description": "Stock quantity for product and warehouse/location.",
        "identity_fields": ["product_uuid", "warehouse_uuid", "location_uuid"],
        "fields": [field("product_uuid", required=True), field("warehouse_uuid"), field("location_uuid"), field("quantity", "number"), field("reserved", "number")],
    },
    {
        "object_type": "InventoryResult",
        "display_name": "Inventory Result",
        "description": "Inventory counting result and discrepancy summary.",
        "identity_fields": ["uuid", "number", "external_id"],
        "fields": [field("uuid"), field("number"), field("warehouse_uuid"), field("status"), field("external_id")],
    },
    {
        "object_type": "PrintJob",
        "display_name": "Print Job",
        "description": "Label, document or industrial printer task.",
        "identity_fields": ["uuid", "name", "external_id"],
        "fields": [field("uuid"), field("name"), field("printer_uuid"), field("site"), field("status"), field("external_id")],
    },
]
