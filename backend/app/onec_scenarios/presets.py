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

BIDIRECTIONAL_SHIPMENT_FACT_DEMO = {
    "key": "mock_wms_shipment_fact_to_onec",
    "name": "WMS ShipmentFact to 1C ERP",
    "description": "Receive WMS shipment facts and update 1C through the OMH HTTP service contract.",
    "source_resource": "Mock WMS ShipmentFact",
    "event_type": "ShipmentFactCreated",
    "entity_type": "ShipmentFact",
    "mappings": ["mock_wms_shipment_fact_to_onec_shipment_fact"],
}

ONEC_SCENARIO_PRESETS = [SALES_ORDER_DEMO, BIDIRECTIONAL_SHIPMENT_FACT_DEMO]
