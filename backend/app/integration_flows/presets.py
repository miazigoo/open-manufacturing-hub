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

TWO_ODATA_TO_ENDPOINT_BUILDER = {
    "version": 1,
    "input": {"endpoint_slug": "onec-pool-to-dnp", "input_mode": "json", "response_mode": "proxy_response"},
    "variables": [
        {"name": "inn", "source": "request.body.inn"},
        {"name": "product_code", "source": "request.body.product_code"},
        {"name": "pool_id", "source": "request.body.pool_id"},
    ],
    "steps": [
        {"id": "read_inn", "type": "read_variable", "name": "Read INN", "path": "request.body.inn", "save_as": "inn"},
        {"id": "read_product_code", "type": "read_variable", "name": "Read product code", "path": "request.body.product_code", "save_as": "product_code"},
        {
            "id": "get_contractor",
            "type": "odata_query",
            "name": "Find contractor by INN",
            "connection": "1C ERP",
            "resource": "Catalog_Контрагенты",
            "filter_builder": [{"field": "ИНН", "operator": "eq", "value": "{{inn}}"}],
            "select": ["Ref_Key", "Description", "ИНН"],
            "top": 1,
            "save_as": "contractor",
            "required": True,
        },
        {
            "id": "get_product",
            "type": "odata_query",
            "name": "Find product by code",
            "connection": "1C ERP",
            "resource": "Catalog_Номенклатура",
            "filter_builder": [{"field": "Артикул", "operator": "eq", "value": "{{product_code}}"}],
            "select": ["Ref_Key", "Description", "Артикул"],
            "top": 1,
            "save_as": "product",
            "required": True,
        },
        {
            "id": "build_payload",
            "type": "build_json",
            "name": "Build DNP payload",
            "save_as": "target_payload",
            "template": {
                "pool_id": "{{request.body.pool_id}}",
                "contractor_uuid": "{{contractor.Ref_Key}}",
                "contractor_name": "{{contractor.Description}}",
                "product_uuid": "{{product.Ref_Key}}",
                "product_name": "{{product.Description}}",
                "codes": "{{request.body.codes}}",
                "source": "1C",
            },
        },
        {"id": "send_to_dnp", "type": "call_endpoint", "name": "Send to DNP API", "connector": "DNP Service", "method": "POST", "path": "/api/marking/pools", "body": "{{target_payload}}", "response_mode": "proxy_response"},
        {"id": "return_dnp_response", "type": "return_response", "name": "Return DNP response", "body": "{{response}}"},
    ],
}

TWO_ODATA_TO_ENDPOINT_PRESET = {
    "name": "1C Pool to DNP via Two OData Queries",
    "slug": "onec-pool-to-dnp",
    "description": "Visual builder demo: read fields from 1C request, run contractor/product OData lookups, build target JSON and send it to DNP API.",
    "source_type": "onec",
    "target_type": "external_api",
    "endpoint": {"input_mode": "json", "response_mode": "proxy_response", "auth_mode": "none", "auth_config_json": {}},
    "matcher_group_json": {"mode": "all", "rules": [{"type": "body_path_exists", "path": "inn"}, {"type": "body_path_exists", "path": "product_code"}, {"type": "body_path_exists", "path": "pool_id"}]},
    "action_json": {"type": "call_rest_api", "target_connector": "DNP Service", "method": "POST", "path": "/api/marking/pools", "body_mode": "json", "payload_source": "target_payload", "response_mode": "proxy_response", "mock_response_json": {"accepted": True, "external_document_id": "DNP-POOL-001"}},
    "response_config_json": {"response_mode": "proxy_response"},
    "builder_json": TWO_ODATA_TO_ENDPOINT_BUILDER,
    "test_payload_json": {"inn": "1234567890", "product_code": "ABC-123", "pool_id": "POOL-001", "codes": ["code1", "code2"]},
}

OPERATION_KEY_ODATA_CHAIN_KEY = "lookup_order_products"

OPERATION_KEY_ODATA_CHAIN_BUILDER = {
    "version": 1,
    "input": {"endpoint_slug": "operation-key-odata-chain", "input_mode": "json", "response_mode": "sync_response"},
    "variables": [
        {"name": "operation_key", "source": "request.body.operation"},
        {"name": "order_number", "source": "request.body.Number"},
    ],
    "steps": [
        {"id": "read_operation_key", "type": "read_variable", "name": "Read operation key", "path": "request.body.operation", "fallback_paths": ["request.body.sinc"], "save_as": "operation_key"},
        {"id": "read_order_number", "type": "read_variable", "name": "Read 1C order number", "path": "request.body.Number", "save_as": "order_number"},
        {
            "id": "find_order",
            "type": "odata_query",
            "name": "Find production order by Number",
            "connection": "1C CHZ OData ERP",
            "resource": "Document_ЗаказНаПроизводство2_2",
            "filter": "Number eq '{{order_number}}'",
            "select": ["Ref_Key", "Number", "Date", "Posted"],
            "top": 1,
            "save_as": "order",
            "required": True,
        },
        {
            "id": "read_products",
            "type": "odata_query",
            "name": "Read production order products",
            "connection": "1C CHZ OData ERP",
            "resource": "Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция",
            "select": ["Номенклатура_Key", "Количество", "КоличествоУпаковок"],
            "top": 10,
            "save_as": "products",
            "required": True,
        },
        {
            "id": "return_order_products",
            "type": "return_response",
            "name": "Return order products",
            "body": {
                "operation_key": "{{operation_key}}",
                "order": "{{order}}",
                "products": "{{products}}",
                "next_manual_step": "Use products[].Номенклатура_Key in the next configured step if the target register supports filtering.",
            },
        },
    ],
}

OPERATION_KEY_ODATA_CHAIN_PRESET = {
    "name": "Operation Key to OData Chained Lookup",
    "slug": "operation-key-odata-chain",
    "description": "Inbound JSON selects a route by operation key. OMH looks up the 1C production order by Number, uses Ref_Key in the next OData resource and returns related rows.",
    "source_type": "external_api",
    "target_type": "odata_lookup",
    "endpoint": {"input_mode": "json", "response_mode": "sync_response", "auth_mode": "none", "auth_config_json": {}},
    "matcher_group_json": {"mode": "all", "rules": [{"type": "body_path_exists", "path": "Number"}]},
    "action_json": {
        "type": "create_event_only",
        "operation": OPERATION_KEY_ODATA_CHAIN_KEY,
        "business_object": "ODataChainedLookup",
        "description": "External system asks OMH to run a chained 1C OData lookup by production order Number.",
    },
    "response_config_json": {"response_mode": "sync_response"},
    "builder_json": OPERATION_KEY_ODATA_CHAIN_BUILDER,
    "test_payload_json": {"operation": OPERATION_KEY_ODATA_CHAIN_KEY, "Number": "260666/6938"},
}

DNP_PULL_CODES_PRESET = OPERATION_KEY_ODATA_CHAIN_PRESET
