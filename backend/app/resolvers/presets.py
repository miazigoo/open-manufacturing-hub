from __future__ import annotations

from typing import Any


def _schema(*fields: str) -> dict[str, Any]:
    return {"type": "object", "properties": {field: {"type": "string"} for field in fields}, "anyOf": fields}


DEFAULT_RESOLVER_PRESETS: list[dict[str, Any]] = [
    {
        "name": "Resolve Customer by INN / UUID / Code",
        "resolver_code": "resolve_customer",
        "object_type": "Customer",
        "strategy": "static_map",
        "input_schema_json": _schema("inn", "uuid", "code"),
        "output_schema_json": {"object_type": "Customer"},
        "config_json": {
            "key_fields": ["uuid", "inn", "code"],
            "cache_key_fields": ["uuid", "inn", "code"],
            "entries": [
                {"match": {"inn": "1234567890"}, "object": {"uuid": "customer-demo-uuid", "inn": "1234567890", "code": "CUST-001", "name": "Demo Customer"}}
            ],
        },
    },
    {
        "name": "Resolve Product by Article / Barcode / GTIN / UUID",
        "resolver_code": "resolve_product",
        "object_type": "Product",
        "strategy": "static_map",
        "input_schema_json": _schema("article", "barcode", "gtin", "uuid", "code"),
        "output_schema_json": {"object_type": "Product"},
        "config_json": {"key_fields": ["uuid", "article", "barcode", "gtin", "code"], "cache_key_fields": ["uuid", "article", "barcode", "gtin", "code"], "entries": [{"match": {"article": "ABC-123"}, "object": {"uuid": "product-abc-123", "article": "ABC-123", "barcode": "4600000000011", "gtin": "04600000000011", "name": "Demo product"}}]},
    },
    {
        "name": "Resolve Warehouse by Code / UUID",
        "resolver_code": "resolve_warehouse",
        "object_type": "Warehouse",
        "strategy": "static_map",
        "input_schema_json": _schema("code", "uuid", "name"),
        "output_schema_json": {"object_type": "Warehouse"},
        "config_json": {"key_fields": ["uuid", "code", "name"], "cache_key_fields": ["uuid", "code", "name"], "entries": [{"match": {"code": "MAIN"}, "object": {"uuid": "warehouse-main", "code": "MAIN", "name": "Main warehouse"}}]},
    },
    {
        "name": "Resolve Sales Order by Number / UUID",
        "resolver_code": "resolve_order",
        "object_type": "SalesOrder",
        "strategy": "static_map",
        "input_schema_json": _schema("number", "uuid"),
        "output_schema_json": {"object_type": "SalesOrder"},
        "config_json": {"key_fields": ["uuid", "number"], "cache_key_fields": ["uuid", "number"], "entries": [{"match": {"number": "SO-1001"}, "object": {"uuid": "sales-order-so-1001", "number": "SO-1001", "status": "new"}}]},
    },
    {
        "name": "Resolve Printer by Name / Site",
        "resolver_code": "resolve_printer",
        "object_type": "PrintJob",
        "strategy": "static_map",
        "input_schema_json": _schema("name", "site"),
        "output_schema_json": {"object_type": "PrintJob"},
        "config_json": {"key_fields": ["name", "site"], "cache_key_fields": ["name", "site"], "entries": [{"match": {"name": "Zebra-01"}, "object": {"uuid": "printer-zebra-01", "name": "Zebra-01", "site": "MAIN", "status": "ready"}}]},
    },
]
