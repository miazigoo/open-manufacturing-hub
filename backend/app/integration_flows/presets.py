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

ONEC_CHZ_POOL_DELIVERY_BUILDER = {
    "version": 1,
    "input": {
        "endpoint_slug": "onec-chz-pool-delivery",
        "input_mode": "json",
        "response_mode": "accepted_event",
        "processing_mode": "async_queue",
    },
    "steps": [
        {
            "id": "deliver_chz_pool",
            "type": "marking_code_pool_export",
            "name": "Save and forward CHZ marking code pool",
            "order_number_path": "request.body.order_number",
            "full_codes_base64_path": "request.body.full_codes_base64",
            "source_document_id_path": "request.body.source_document_id",
            "source_document_name_path": "request.body.source_document_name",
            # destination_path tells OMH where to read the destination field from the 1C request.
            # Values: "laser" or "not_specified" -> save laser file (default behaviour);
            #         "print" -> skip laser file copy, only DnP forward.
            # Remove or leave empty to always use global CHZ Delivery settings.
            "destination_path": "request.body.destination",
            "allow_overwrite": True,
            "save_as": "marking_pool_export",
            "metadata_json": {"scenario": "onec_chz_pool_delivery"},
        },
        {
            "id": "return_delivery_result",
            "type": "return_response",
            "name": "Return CHZ delivery result",
            "body": "{{marking_pool_export}}",
            "status_code": 200,
        },
    ],
}


ONEC_CHZ_POOL_DELIVERY_PRESET = {
    "name": "1C CHZ Code Pool Delivery",
    "slug": "onec-chz-pool-delivery",
    "description": "Visible OMH endpoint for 1C: accepts CHZ full marking codes in Base64, saves the laser file through configured CHZ delivery settings and forwards the same pool to DnP.",
    "source_type": "onec",
    "target_type": "internal",
    "endpoint": {"input_mode": "json", "response_mode": "accepted_event", "processing_mode": "async_queue", "auth_mode": "none", "auth_config_json": {}},
    "matcher_group_json": {
        "mode": "all",
        "rules": [
            {"type": "body_path_exists", "path": "order_number"},
            {"type": "body_path_exists", "path": "full_codes_base64"},
        ],
    },
    "action_json": {
        "type": "create_event_only",
        "operation": "chz_pool_delivery",
        "business_object": "MarkingCodePoolDelivery",
        "description": "1C pushes a CHZ marking code pool to OMH for file delivery and DnP synchronization.",
    },
    "response_config_json": {"response_mode": "accepted_event", "processing_mode": "async_queue"},
    "builder_json": ONEC_CHZ_POOL_DELIVERY_BUILDER,
    "test_payload_json": {
        "order_number": "260703/5442",
        "source_document_id": "AEAE-000137",
        "source_document_name": "Заказ на эмиссию кодов маркировки AEAE-000137",
        "full_codes_base64": ["MDEwNDY0NjE1MTY5NzE4NjIxNV88cWxrPFpiQ1dGUD5XMilmb1UdOTNsemhV"],
        "destination": "laser",
    },
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

B2B_PORTAL_ORDER_BUILDER = {
    "version": 1,
    "input": {"endpoint_slug": "b2b-portal-order", "input_mode": "json", "response_mode": "proxy_response", "processing_mode": "sync_inline"},
    "steps": [
        {
            "id": "extract_order",
            "type": "extract",
            "name": "Validate portal order fields",
            "source": "request.body",
            "fields": [
                {"name": "order_number", "path": "order.number", "required": True},
                {"name": "customer_name", "path": "order.customer.name", "required": True},
                {"name": "customer_inn", "path": "order.customer.inn", "required": False},
                {"name": "items", "path": "order.items", "required": True},
                {"name": "portal", "path": "portal", "required": False},
            ],
        },
        {
            "id": "build_canonical",
            "type": "build_json",
            "name": "Build canonical order",
            "template": {
                "doc_type": "SalesOrderFromPortal",
                "number": "{{order_number}}",
                "customer": {"name": "{{customer_name}}", "inn": "{{customer_inn}}"},
                "source_portal": "{{portal}}",
                "rows": "{{items}}",
                "received_via": "b2b-portal-order",
            },
            "save_as": "canonical_order",
        },
        {
            "id": "send_to_onec",
            "type": "call_endpoint",
            "name": "Send canonical order to 1C",
            "connector": "1C ERP",
            "method": "POST",
            "path": "/hs/omh/orders",
            "headers": {"Content-Type": "application/json"},
            "body": "{{canonical_order}}",
            "save_response_as": "onec_response",
            "mock_response_json": {"ok": True, "order_guid": "preview-order-guid"},
        },
        {
            "id": "return_result",
            "type": "return_response",
            "name": "Return result to portal",
            "body": {"accepted": True, "order_number": "{{order_number}}", "onec": "{{onec_response}}"},
            "status_code": 200,
        },
    ],
}

B2B_PORTAL_ORDER_PRESET = {
    "name": "B2B Portal Order to 1C (canonical)",
    "slug": "b2b-portal-order",
    "description": "Webhook for a client B2B portal: validate the order JSON with readable errors, map it to the canonical OMH order format and forward it to the 1C HTTP service. Duplicate the flow and change the slug for each new portal.",
    "source_type": "webhook",
    "target_type": "onec",
    "endpoint": {"input_mode": "json", "response_mode": "proxy_response", "processing_mode": "sync_inline", "auth_mode": "none", "auth_config_json": {}},
    "matcher_group_json": {"mode": "all", "rules": [{"type": "body_path_exists", "path": "order.number"}]},
    "action_json": {"type": "create_event_only", "operation": "b2b_portal_order", "business_object": "PortalOrder"},
    "response_config_json": {"response_mode": "proxy_response"},
    "builder_json": B2B_PORTAL_ORDER_BUILDER,
    "test_payload_json": {
        "portal": "portal-a",
        "order": {
            "number": "PO-1001",
            "customer": {"name": "ООО Тест", "inn": "1234567890"},
            "items": [{"sku": "ABC-1", "qty": 2, "price": 150.0}],
        },
    },
}

OZON_ORDERS_TO_ONEC_BUILDER = {
    "version": 1,
    "input": {"endpoint_slug": "ozon-orders-to-onec", "input_mode": "json", "response_mode": "sync_response", "processing_mode": "sync_inline"},
    "steps": [
        {
            "id": "pull_ozon_orders",
            "type": "ozon_action",
            "name": "Pull new FBS orders from Ozon",
            "action": "list_orders",
            "connector": "Ozon Seller",
            "since": "{{request.body.ozon_since}}",
            "limit": 100,
            "save_as": "ozon_orders",
            "run_if": {"mode": "all", "rules": [{"type": "always"}]},
        },
        {
            "id": "build_onec_orders",
            "type": "build_json",
            "name": "Map Ozon orders to canonical 1C orders",
            "template": {
                "doc_type": "MarketplaceOrdersBatch",
                "marketplace": "ozon",
                "count": "{{ozon_orders.count}}",
                "orders": "{{ozon_orders.orders}}",
            },
            "save_as": "onec_orders",
        },
        {
            "id": "send_to_onec",
            "type": "call_endpoint",
            "name": "Send orders batch to 1C",
            "connector": "1C ERP",
            "method": "POST",
            "path": "/hs/omh/marketplace/orders",
            "headers": {"Content-Type": "application/json"},
            "body": "{{onec_orders}}",
            "save_response_as": "onec_response",
            "mock_response_json": {"ok": True, "created": 1},
        },
        {
            "id": "save_sync_marker",
            "type": "build_json",
            "name": "Store sync marker for the next run",
            "template": {"ozon_since": "{{request.body.ozon_since}}"},
            "save_as": "sync_state",
        },
        {
            "id": "return_result",
            "type": "return_response",
            "name": "Return sync result",
            "body": {"ok": True, "orders": "{{ozon_orders.count}}", "onec": "{{onec_response}}"},
        },
    ],
}

OZON_ORDERS_TO_ONEC_PRESET = {
    "name": "Ozon orders to 1C (FBS)",
    "slug": "ozon-orders-to-onec",
    "description": "Pull new FBS orders from Ozon Seller API, normalize them to the canonical marketplace order format and send the batch to the 1C HTTP service. Connector 'Ozon Seller' needs client_id/api_key.",
    "source_type": "external_api",
    "target_type": "onec",
    "endpoint": {"input_mode": "json", "response_mode": "sync_response", "processing_mode": "sync_inline", "auth_mode": "none", "auth_config_json": {}},
    "matcher_group_json": {"mode": "all", "rules": [{"type": "always"}]},
    "action_json": {"type": "create_event_only", "operation": "ozon_orders_sync", "business_object": "MarketplaceOrder"},
    "response_config_json": {"response_mode": "sync_response"},
    "builder_json": OZON_ORDERS_TO_ONEC_BUILDER,
    "test_payload_json": {"trigger": "manual"},
}

OZON_STOCKS_PRICES_FROM_ONEC_BUILDER = {
    "version": 1,
    "input": {"endpoint_slug": "ozon-stocks-prices-from-onec", "input_mode": "json", "response_mode": "sync_response", "processing_mode": "sync_inline"},
    "steps": [
        {
            "id": "extract_rows",
            "type": "extract",
            "name": "Validate 1C rows",
            "source": "request.body",
            "fields": [
                {"name": "stocks", "path": "stocks", "required": False},
                {"name": "prices", "path": "prices", "required": False},
            ],
        },
        {
            "id": "push_stocks",
            "type": "ozon_action",
            "name": "Update stocks in Ozon",
            "action": "update_stocks",
            "connector": "Ozon Seller",
            "stocks_path": "stocks",
            "save_as": "stocks_result",
            "run_if": {"mode": "all", "rules": [{"type": "body_path_exists", "path": "request.body.stocks"}]},
        },
        {
            "id": "push_prices",
            "type": "ozon_action",
            "name": "Update prices in Ozon",
            "action": "update_prices",
            "connector": "Ozon Seller",
            "prices_path": "prices",
            "save_as": "prices_result",
            "run_if": {"mode": "all", "rules": [{"type": "body_path_exists", "path": "request.body.prices"}]},
        },
        {
            "id": "return_result",
            "type": "return_response",
            "name": "Return update results",
            "body": {"stocks": "{{stocks_result}}", "prices": "{{prices_result}}"},
        },
    ],
}

OZON_STOCKS_PRICES_FROM_ONEC_PRESET = {
    "name": "1C stocks and prices to Ozon",
    "slug": "ozon-stocks-prices-from-onec",
    "description": "1C pushes stock and/or price rows keyed by offer_id; OMH updates Ozon Seller API in batches and returns per-item updated/errors so bad offers become incidents instead of silent failures.",
    "source_type": "onec",
    "target_type": "external_api",
    "endpoint": {"input_mode": "json", "response_mode": "sync_response", "processing_mode": "sync_inline", "auth_mode": "none", "auth_config_json": {}},
    "matcher_group_json": {"mode": "any", "rules": [{"type": "body_path_exists", "path": "stocks"}, {"type": "body_path_exists", "path": "prices"}]},
    "action_json": {"type": "create_event_only", "operation": "ozon_stocks_prices_sync", "business_object": "MarketplaceStockPrice"},
    "response_config_json": {"response_mode": "sync_response"},
    "builder_json": OZON_STOCKS_PRICES_FROM_ONEC_BUILDER,
    "test_payload_json": {
        "stocks": [{"offer_id": "ABC-123", "qty": 15}],
        "prices": [{"offer_id": "ABC-123", "price": "100.00", "old_price": "120.00", "min_price": "80.00"}],
    },
}
