from __future__ import annotations

from typing import Any

CONTRACT_PRESETS: list[dict[str, Any]] = [
    {
        "code": "dnp_chz_codes_import_request",
        "name": "DNP — импорт кодов ЧЗ: request",
        "kind": "operation_request",
        "owner_type": "operation_profile",
        "description": "Контракт payload для отправки массива кодов Честного знака во внешний DNP endpoint.",
        "operation_profile_code": "dnp_import_chz_codes",
        "schema_json": {
            "type": "object",
            "fields": [
                {"path": "omh.run_id", "type": "string", "required": True, "label": "Run ID", "description": "Идентификатор запуска OMH", "example": "run-001"},
                {"path": "omh.event_id", "type": "string", "required": True, "label": "Event ID", "example": "evt-001"},
                {"path": "omh.event_type", "type": "string", "required": True, "label": "Тип события", "example": "ChestniyZnakCodesSyncRequested"},
                {"path": "omh.entity_id", "type": "string", "required": False, "label": "Business key", "example": "260666/6938"},
                {"path": "payload.order_ref_key", "type": "guid", "required": False, "label": "Ref_Key заказа 1С", "example": "4f1f5c6d-2d3a-11ef-9c7a-005056a1b2c3"},
                {"path": "payload.order_number", "type": "string", "required": True, "label": "Номер заказа 1С", "example": "260666/6938"},
                {"path": "payload.rows", "type": "array", "required": True, "label": "Коды маркировки", "description": "Массив строк/объектов ЧЗ, должен остаться array", "example": [{"code": "0104600439937818215ABC"}]},
            ],
        },
        "example_json": {
            "omh": {"run_id": "run-001", "event_id": "evt-001", "event_type": "ChestniyZnakCodesSyncRequested", "entity_id": "260666/6938"},
            "payload": {"order_ref_key": "4f1f5c6d-2d3a-11ef-9c7a-005056a1b2c3", "order_number": "260666/6938", "rows": [{"code": "0104600439937818215ABC"}]},
        },
    },
    {
        "code": "onec_write_external_id_request",
        "name": "1C — записать external_id заказа: request",
        "kind": "operation_request",
        "owner_type": "operation_profile",
        "description": "Контракт записи external_id, полученного от сайта/API, обратно в 1С.",
        "operation_profile_code": "onec_write_order_external_id",
        "schema_json": {
            "type": "object",
            "fields": [
                {"path": "order_ref_key", "type": "guid", "required": True, "label": "Ref_Key заказа 1С"},
                {"path": "order_number", "type": "string", "required": True, "label": "Номер заказа"},
                {"path": "external_system", "type": "string", "required": True, "label": "Внешняя система", "example": "website"},
                {"path": "external_id", "type": "string", "required": True, "label": "ID во внешней системе"},
                {"path": "status", "type": "string", "required": False, "label": "Статус"},
            ],
        },
        "example_json": {"order_ref_key": "4f1f5c6d-2d3a-11ef-9c7a-005056a1b2c3", "order_number": "SO-1001", "external_system": "website", "external_id": "SITE-123", "status": "accepted"},
    },
    {
        "code": "onec_shipment_fact_request",
        "name": "1C — принять факт отгрузки WMS: request",
        "kind": "operation_request",
        "owner_type": "operation_profile",
        "description": "Контракт payload для передачи факта отгрузки WMS в 1С HTTP Service.",
        "operation_profile_code": "onec_accept_wms_shipment_fact",
        "schema_json": {
            "type": "object",
            "fields": [
                {"path": "omh.event_id", "type": "string", "required": True, "label": "Event ID"},
                {"path": "payload.order_ref_key", "type": "guid", "required": False, "label": "Ref_Key заказа 1С"},
                {"path": "payload.wms_shipment_id", "type": "string", "required": True, "label": "ID отгрузки WMS"},
                {"path": "payload.order_number", "type": "string", "required": False, "label": "Номер заказа"},
                {"path": "payload.status", "type": "string", "required": False, "label": "Статус"},
                {"path": "payload.items", "type": "array", "required": True, "label": "Строки отгрузки"},
            ],
        },
        "example_json": {"omh": {"event_id": "evt-wms-001"}, "payload": {"order_ref_key": "4f1f5c6d-2d3a-11ef-9c7a-005056a1b2c3", "wms_shipment_id": "WMS-1001", "items": [{"sku": "SKU-1", "qty": 2}]}},
    },
    {
        "code": "website_order_import_request",
        "name": "Сайт/API — импорт заказа: request",
        "kind": "operation_request",
        "owner_type": "integration_pattern",
        "description": "Контракт payload для отправки заказа из 1С/OData во внешний сайт или Web API.",
        "schema_json": {
            "type": "object",
            "fields": [
                {"path": "source", "type": "string", "required": True, "label": "Источник", "example": "OMH"},
                {"path": "site_code", "type": "string", "required": True, "label": "Код сайта"},
                {"path": "order.uuid", "type": "guid", "required": True, "label": "UUID заказа"},
                {"path": "order.number", "type": "string", "required": True, "label": "Номер заказа"},
                {"path": "order.date", "type": "datetime", "required": False, "label": "Дата заказа"},
            ],
        },
        "example_json": {"source": "OMH", "site_code": "main", "order": {"uuid": "4f1f5c6d-2d3a-11ef-9c7a-005056a1b2c3", "number": "SO-1001", "date": "2026-07-13T10:00:00"}},
    },
]

MAPPING_PRESETS: list[dict[str, Any]] = [
    {
        "code": "mapping_dnp_chz_codes_import",
        "name": "DNP — импорт кодов ЧЗ",
        "description": "Собирает payload для операции dnp_import_chz_codes из request, OData заказа и результата foreach по кодам ЧЗ.",
        "target_contract_code": "dnp_chz_codes_import_request",
        "operation_profile_code": "dnp_import_chz_codes",
        "package_id": "omh-package-onec",
        "source_context_json": {
            "context": {"run_id": "run-001", "event_id": "evt-001"},
            "request": {"body": {"order_id": "4f1f5c6d-2d3a-11ef-9c7a-005056a1b2c3", "order_name": "260666/6938"}},
            "order": {"Ref_Key": "4f1f5c6d-2d3a-11ef-9c7a-005056a1b2c3", "Number": "260666/6938"},
            "codes": [{"code": "0104600439937818215ABC", "nomenclature_key": "NOM-1"}],
        },
        "mapping_json": {
            "version": 1,
            "target_contract_code": "dnp_chz_codes_import_request",
            "fields": [
                {"target_path": "omh.run_id", "source_type": "variable", "source": "context.run_id", "preserve_type": True},
                {"target_path": "omh.event_id", "source_type": "variable", "source": "context.event_id", "preserve_type": True},
                {"target_path": "omh.event_type", "source_type": "constant", "value": "ChestniyZnakCodesSyncRequested"},
                {"target_path": "omh.entity_id", "source_type": "variable", "source": "request.body.order_name", "preserve_type": True},
                {"target_path": "payload.order_ref_key", "source_type": "variable", "source": "order.Ref_Key", "preserve_type": True},
                {"target_path": "payload.order_number", "source_type": "variable", "source": "order.Number", "preserve_type": True},
                {"target_path": "payload.rows", "source_type": "variable", "source": "codes", "preserve_type": True},
            ],
            "dynamic_entries": [],
        },
    },
    {
        "code": "mapping_onec_write_external_id",
        "name": "1C — записать external_id заказа",
        "description": "Собирает payload записи external_id сайта/API обратно в 1С.",
        "target_contract_code": "onec_write_external_id_request",
        "operation_profile_code": "onec_write_order_external_id",
        "package_id": "omh-package-onec",
        "source_context_json": {
            "request": {"body": {"site_code": "main"}},
            "order": {"Ref_Key": "4f1f5c6d-2d3a-11ef-9c7a-005056a1b2c3", "Number": "SO-1001"},
            "site_response": {"external_id": "SITE-123", "status": "accepted"},
        },
        "mapping_json": {
            "version": 1,
            "target_contract_code": "onec_write_external_id_request",
            "fields": [
                {"target_path": "order_ref_key", "source_type": "variable", "source": "order.Ref_Key", "preserve_type": True},
                {"target_path": "order_number", "source_type": "variable", "source": "order.Number", "preserve_type": True},
                {"target_path": "external_system", "source_type": "constant", "value": "website"},
                {"target_path": "external_id", "source_type": "variable", "source": "site_response.external_id", "preserve_type": True},
                {"target_path": "status", "source_type": "variable", "source": "site_response.status", "preserve_type": True},
            ],
            "dynamic_entries": [],
        },
    },
    {
        "code": "mapping_onec_shipment_fact",
        "name": "WMS -> 1C — факт отгрузки",
        "description": "Собирает payload факта отгрузки WMS для 1С HTTP Service.",
        "target_contract_code": "onec_shipment_fact_request",
        "operation_profile_code": "onec_accept_wms_shipment_fact",
        "package_id": "omh-package-onec",
        "source_context_json": {
            "context": {"event_id": "evt-wms-001"},
            "request": {"body": {"wms_shipment_id": "WMS-1001", "order_number": "SO-1001", "status": "shipped", "items": [{"sku": "SKU-1", "qty": 2}]}},
            "order": {"Ref_Key": "4f1f5c6d-2d3a-11ef-9c7a-005056a1b2c3", "Number": "SO-1001"},
        },
        "mapping_json": {
            "version": 1,
            "target_contract_code": "onec_shipment_fact_request",
            "fields": [
                {"target_path": "omh.event_id", "source_type": "variable", "source": "context.event_id", "preserve_type": True},
                {"target_path": "payload.order_ref_key", "source_type": "variable", "source": "order.Ref_Key", "preserve_type": True},
                {"target_path": "payload.wms_shipment_id", "source_type": "variable", "source": "request.body.wms_shipment_id", "preserve_type": True},
                {"target_path": "payload.order_number", "source_type": "variable", "source": "request.body.order_number", "preserve_type": True},
                {"target_path": "payload.status", "source_type": "variable", "source": "request.body.status", "preserve_type": True},
                {"target_path": "payload.items", "source_type": "variable", "source": "request.body.items", "preserve_type": True},
            ],
            "dynamic_entries": [],
        },
    },
    {
        "code": "mapping_website_order_import",
        "name": "Сайт/API — импорт заказа",
        "description": "Собирает payload отправки заказа из 1С/OData во внешний сайт или Web API.",
        "target_contract_code": "website_order_import_request",
        "operation_profile_code": None,
        "source_context_json": {
            "request": {"body": {"site_code": "main"}},
            "order": {"Ref_Key": "4f1f5c6d-2d3a-11ef-9c7a-005056a1b2c3", "Number": "SO-1001", "Date": "2026-07-13T10:00:00"},
        },
        "mapping_json": {
            "version": 1,
            "target_contract_code": "website_order_import_request",
            "fields": [
                {"target_path": "source", "source_type": "constant", "value": "OMH"},
                {"target_path": "site_code", "source_type": "variable", "source": "request.body.site_code", "preserve_type": True},
                {"target_path": "order.uuid", "source_type": "variable", "source": "order.Ref_Key", "preserve_type": True},
                {"target_path": "order.number", "source_type": "variable", "source": "order.Number", "preserve_type": True},
                {"target_path": "order.date", "source_type": "variable", "source": "order.Date", "preserve_type": True},
            ],
            "dynamic_entries": [],
        },
    },
]
