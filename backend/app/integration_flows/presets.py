MARKING_POOL_PRESET = {
    "name": "1C Marking Code Pool to Internal Service",
    "slug": "marking-pool",
    "description": "Route 1C marking code pools by DNP key and forward them to an internal DNP REST service.",
    "source_type": "onec",
    "target_type": "external_api",
    "endpoint": {"input_mode": "json", "response_mode": "proxy_response", "auth_mode": "none", "auth_config_json": {}},
    "matcher_group_json": {"mode": "any", "rules": [{"type": "body_path_equals", "path": "pool_type", "value": "DNP"}, {"type": "text_contains", "value": "DNP"}]},
    "action_json": {"type": "call_rest_api", "target_connector": "DNP Service", "method": "POST", "path": "/api/marking/codes/pool", "body_mode": "json", "payload_source": "incoming_payload", "response_mode": "proxy_response"},
    "response_config_json": {"response_mode": "proxy_response"},
    "test_payload_json": {"pool_type": "DNP", "order_id": "ORD-123", "codes": ["010464615169738421ABC", "010464615169738421DEF"]},
}
