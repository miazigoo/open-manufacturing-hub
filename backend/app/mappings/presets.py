ONEC_SALES_ORDER_TO_CANONICAL = {
    "name": "onec_sales_order_to_canonical_sales_order",
    "description": "1C OData sales order to canonical SalesOrder",
    "source_entity": "1c.Document_ЗаказКлиента",
    "target_entity": "canonical.SalesOrder",
    "rules_json": [
        {"from": "Ref_Key", "to": "external_id"},
        {"from": "Number", "to": "number"},
        {"from": "Date", "to": "date"},
        {"from": "Партнер_Key", "to": "customer.external_id"},
        {"from": "Склад_Key", "to": "warehouse.external_id"},
        {"from": "Комментарий", "to": "comment"},
        {"from": "Товары", "to": "items", "type": "array", "item_rules": [
            {"from": "Номенклатура_Key", "to": "product_external_id"},
            {"from": "Количество", "to": "quantity"},
            {"from": "Цена", "to": "price"},
        ]},
    ],
    "source_schema_json": {"Ref_Key": "string", "Number": "string", "Товары": []},
    "target_schema_json": {"external_id": "string", "items": []},
}

CANONICAL_SALES_ORDER_TO_MOCK_WMS = {
    "name": "canonical_sales_order_to_mock_wms_shipment_order",
    "description": "Canonical SalesOrder to Mock WMS shipment order",
    "source_entity": "canonical.SalesOrder",
    "target_entity": "mock_wms.ShipmentOrder",
    "rules_json": [
        {"constant": "create_shipment_order", "target": "_omh.operation"},
        {"constant": "POST", "target": "_omh.method"},
        {"constant": "/shipment-orders", "target": "_omh.path"},
        {"source": "external_id", "target": "document.external_id"},
        {"source": "number", "target": "document.number"},
        {"constant": "MAIN", "target": "document.warehouse_id"},
        {"source": "items", "target": "document.items", "type": "array", "items": [
            {"source": "product_external_id", "target": "sku"},
            {"source": "quantity", "target": "qty"},
        ]},
    ],
    "source_schema_json": {"external_id": "string", "items": []},
    "target_schema_json": {"_omh": {}, "document": {"items": []}},
}

MAPPING_PRESETS = [ONEC_SALES_ORDER_TO_CANONICAL, CANONICAL_SALES_ORDER_TO_MOCK_WMS]
