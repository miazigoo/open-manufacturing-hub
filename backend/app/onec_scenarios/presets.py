SALES_ORDER_DEMO = {
    "key": "onec_sales_order_to_mock_wms",
    "name": "1C SalesOrder to Mock WMS ShipmentOrder",
    "description": "Poll 1C OData sales orders, normalize them to canonical SalesOrder, then create Mock WMS shipment orders.",
    "source_resource": "Document_ЗаказКлиента",
    "event_type": "SalesOrderCreated",
    "entity_type": "SalesOrder",
    "mappings": [
        "onec_sales_order_to_canonical_sales_order",
        "canonical_sales_order_to_mock_wms_shipment_order",
    ],
}

ONEC_SCENARIO_PRESETS = [SALES_ORDER_DEMO]
