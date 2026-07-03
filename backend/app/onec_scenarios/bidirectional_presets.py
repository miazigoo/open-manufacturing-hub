BIDIRECTIONAL_WORKFLOW_NAME = "WMS ShipmentFact to 1C ERP"
BIDIRECTIONAL_MAPPING_NAME = "mock_wms_shipment_fact_to_onec_shipment_fact"
BIDIRECTIONAL_EVENT_TYPE = "ShipmentFactCreated"
BIDIRECTIONAL_ENTITY_TYPE = "ShipmentFact"
BIDIRECTIONAL_SOURCE_SYSTEM = "Mock WMS"
BIDIRECTIONAL_TARGET_SYSTEM = "Demo 1C ERP"

STOCK_BALANCE_WORKFLOW_NAME = "WMS StockBalance to 1C ERP"
STOCK_BALANCE_MAPPING_NAME = "mock_wms_stock_balance_to_onec_stock_balance"
STOCK_BALANCE_EVENT_TYPE = "StockBalanceChanged"
STOCK_BALANCE_ENTITY_TYPE = "StockBalance"

INVENTORY_RESULT_WORKFLOW_NAME = "WMS InventoryResult to 1C ERP"
INVENTORY_RESULT_MAPPING_NAME = "mock_wms_inventory_result_to_onec_inventory_result"
INVENTORY_RESULT_EVENT_TYPE = "InventoryResultCreated"
INVENTORY_RESULT_ENTITY_TYPE = "InventoryResult"

BIDIRECTIONAL_WORKFLOW_STEPS = [
    {"name": "receive"},
    {"name": "maintenance_guard"},
    {"name": "map_payload", "config": {"mapping": BIDIRECTIONAL_MAPPING_NAME}},
    {"name": "call_connector"},
    {"name": "handle_response"},
    {"name": "create_incident", "on": "failure"},
    {"name": "send_notifications", "on": "failure"},
]


def reverse_workflow_steps(mapping_name: str) -> list[dict[str, object]]:
    return [
        {"name": "receive"},
        {"name": "maintenance_guard"},
        {"name": "map_payload", "config": {"mapping": mapping_name}},
        {"name": "call_connector"},
        {"name": "handle_response"},
        {"name": "create_incident", "on": "failure"},
        {"name": "send_notifications", "on": "failure"},
    ]
