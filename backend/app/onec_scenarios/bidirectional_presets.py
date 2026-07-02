BIDIRECTIONAL_WORKFLOW_NAME = "WMS ShipmentFact to 1C ERP"
BIDIRECTIONAL_MAPPING_NAME = "mock_wms_shipment_fact_to_onec_shipment_fact"
BIDIRECTIONAL_EVENT_TYPE = "ShipmentFactCreated"
BIDIRECTIONAL_ENTITY_TYPE = "ShipmentFact"
BIDIRECTIONAL_SOURCE_SYSTEM = "Mock WMS"
BIDIRECTIONAL_TARGET_SYSTEM = "Demo 1C ERP"

BIDIRECTIONAL_WORKFLOW_STEPS = [
    {"name": "receive"},
    {"name": "maintenance_guard"},
    {"name": "map_payload", "config": {"mapping": BIDIRECTIONAL_MAPPING_NAME}},
    {"name": "call_connector"},
    {"name": "handle_response"},
    {"name": "create_incident", "on": "failure"},
    {"name": "send_notifications", "on": "failure"},
]
