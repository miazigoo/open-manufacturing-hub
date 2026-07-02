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

MOCK_WMS_SHIPMENT_FACT_TO_ONEC = {
    "name": "mock_wms_shipment_fact_to_onec_shipment_fact",
    "description": "Mock WMS ShipmentFact to 1C HTTP service shipment fact envelope",
    "source_entity": "mock_wms.ShipmentFact",
    "target_entity": "1c.ShipmentFact",
    "rules_json": [
        {"constant": "update_shipment_status", "target": "_omh.operation"},
        {"constant": "ShipmentFactCreated", "target": "omh.event_type"},
        {"constant": "ShipmentFact", "target": "omh.entity_type"},
        {"source": "order_id", "target": "payload.external_order_id"},
        {"source": "shipment_id", "target": "payload.shipment_id"},
        {"source": "status", "target": "payload.status"},
        {"source": "warehouse_id", "target": "payload.warehouse_id"},
        {"source": "items", "target": "payload.items", "type": "array", "items": [
            {"source": "sku", "target": "sku"},
            {"source": "qty", "target": "quantity"},
        ]},
    ],
    "source_schema_json": {"shipment_id": "string", "order_id": "string", "items": []},
    "target_schema_json": {"_omh": {}, "omh": {}, "payload": {"items": []}},
}

MAPPING_PRESETS = [ONEC_SALES_ORDER_TO_CANONICAL, CANONICAL_SALES_ORDER_TO_MOCK_WMS, MOCK_WMS_SHIPMENT_FACT_TO_ONEC]
