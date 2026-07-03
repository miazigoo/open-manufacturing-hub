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

WMS_STOCK_BALANCE_TO_ONEC_DEMO = {
    "key": "mock_wms_stock_balance_to_onec",
    "name": "WMS StockBalance to 1C ERP",
    "description": "Receive WMS stock balance snapshots and update 1C through the OMH HTTP service contract.",
    "source_resource": "Mock WMS StockBalance",
    "event_type": "StockBalanceChanged",
    "entity_type": "StockBalance",
    "mappings": ["mock_wms_stock_balance_to_onec_stock_balance"],
}

WMS_INVENTORY_RESULT_TO_ONEC_DEMO = {
    "key": "mock_wms_inventory_result_to_onec",
    "name": "WMS InventoryResult to 1C ERP",
    "description": "Receive WMS inventory count results and send them to 1C through the OMH HTTP service contract.",
    "source_resource": "Mock WMS InventoryResult",
    "event_type": "InventoryResultCreated",
    "entity_type": "InventoryResult",
    "mappings": ["mock_wms_inventory_result_to_onec_inventory_result"],
}

FULL_ERP_WMS_INTEGRATION = {
    "key": "onec_erp_wms_full",
    "name": "1C ERP and 1C WMS full exchange",
    "description": "Install the standard bidirectional ERP/WMS exchange: ERP sales orders to WMS plus WMS shipment facts, balances and inventory results back to ERP.",
    "source_resource": "Document_ЗаказКлиента + WMS operational facts",
    "event_type": "Multiple",
    "entity_type": "Multiple",
    "mappings": [
        "onec_sales_order_to_canonical_sales_order",
        "canonical_sales_order_to_mock_wms_shipment_order",
        "mock_wms_shipment_fact_to_onec_shipment_fact",
        "mock_wms_stock_balance_to_onec_stock_balance",
        "mock_wms_inventory_result_to_onec_inventory_result",
    ],
}

ONEC_SCENARIO_PRESETS = [
    SALES_ORDER_DEMO,
    BIDIRECTIONAL_SHIPMENT_FACT_DEMO,
    WMS_STOCK_BALANCE_TO_ONEC_DEMO,
    WMS_INVENTORY_RESULT_TO_ONEC_DEMO,
    FULL_ERP_WMS_INTEGRATION,
]
