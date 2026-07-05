from __future__ import annotations

from typing import Any

ERP_ODATA: dict[str, list[dict[str, Any]]] = {
    "Catalog_Контрагенты": [
        {"Ref_Key": "11111111-1111-1111-1111-111111111111", "Code": "000000001", "Description": "ООО Ромашка", "ИНН": "7707083893", "DeletionMark": False},
        {"Ref_Key": "22222222-2222-2222-2222-222222222222", "Code": "000000002", "Description": "ООО Василек", "ИНН": "7708123456", "DeletionMark": False},
        {"Ref_Key": "33333333-3333-3333-3333-333333333333", "Code": "000000003", "Description": "Удаленный контрагент", "ИНН": "0000000000", "DeletionMark": True},
    ],
    "Catalog_Номенклатура": [
        {"Ref_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "Code": "000000001", "Description": "Сок яблочный 1л", "Артикул": "A-100", "GTIN": "04640123456789", "DeletionMark": False},
        {"Ref_Key": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "Code": "000000002", "Description": "Вода питьевая 0.5л", "Артикул": "W-050", "GTIN": "04640987654321", "DeletionMark": False},
        {"Ref_Key": "cccccccc-cccc-cccc-cccc-cccccccccccc", "Code": "000000003", "Description": "Архивный товар", "Артикул": "OLD-001", "GTIN": "00000000000000", "DeletionMark": True},
    ],
    "Document_ЗаказКлиента": [
        {"Ref_Key": "44444444-4444-4444-4444-444444444444", "Number": "SO-1001", "Date": "2026-07-01T10:00:00", "Posted": True, "Контрагент_Key": "11111111-1111-1111-1111-111111111111", "DeletionMark": False},
        {"Ref_Key": "55555555-5555-5555-5555-555555555555", "Number": "SO-1002", "Date": "2026-07-02T11:30:00", "Posted": False, "Контрагент_Key": "22222222-2222-2222-2222-222222222222", "DeletionMark": False},
    ],
    "Catalog_Склады": [
        {"Ref_Key": "warehouse-main", "Code": "000000001", "Description": "Основной склад", "DeletionMark": False},
        {"Ref_Key": "warehouse-factory", "Code": "000000002", "Description": "Склад производства", "DeletionMark": False},
    ],
}

WMS_ODATA: dict[str, list[dict[str, Any]]] = {
    "Catalog_Склады": [
        {"Ref_Key": "wms-main", "Code": "WMS-001", "Description": "WMS Основной склад", "DeletionMark": False},
        {"Ref_Key": "wms-pick", "Code": "WMS-002", "Description": "WMS Зона подбора", "DeletionMark": False},
    ],
    "Catalog_Ячейки": [
        {"Ref_Key": "cell-a-01", "Code": "A-01-01", "Description": "A-01-01", "Склад_Key": "wms-main", "DeletionMark": False},
        {"Ref_Key": "cell-b-02", "Code": "B-02-03", "Description": "B-02-03", "Склад_Key": "wms-pick", "DeletionMark": False},
    ],
    "InformationRegister_Остатки": [
        {"Склад_Key": "wms-main", "Ячейка_Key": "cell-a-01", "Номенклатура_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "Количество": 120},
        {"Склад_Key": "wms-pick", "Ячейка_Key": "cell-b-02", "Номенклатура_Key": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "Количество": 32},
    ],
}

TRAINING_CONNECTORS = [
    {
        "name": "Training OData ERP",
        "connector_type": "onec",
        "direction": "bidirectional",
        "config_json": {
            "base_url": "/api/training/mock-odata/erp/odata/standard.odata",
            "auth": {"type": "none"},
            "odata": {"enabled": True, "default_page_size": 20, "max_pages": 1},
            "omh": {"profile": "odata_connection", "description": "Training mock ERP OData", "tags": ["training", "erp", "mock"]},
            "mock_odata": ERP_ODATA,
        },
    },
    {
        "name": "Training OData WMS",
        "connector_type": "onec",
        "direction": "bidirectional",
        "config_json": {
            "base_url": "/api/training/mock-odata/wms/odata/standard.odata",
            "auth": {"type": "none"},
            "odata": {"enabled": True, "default_page_size": 20, "max_pages": 1},
            "omh": {"profile": "odata_connection", "description": "Training mock WMS/УСП OData", "tags": ["training", "wms", "mock"]},
            "mock_odata": WMS_ODATA,
        },
    },
    {
        "name": "Training DNP API",
        "connector_type": "rest",
        "direction": "target",
        "config_json": {"url": "/api/training/mock-dnp/marking/pools", "method": "POST", "training_mock_dnp": True},
    },
    {
        "name": "Training Printer",
        "connector_type": "rest",
        "direction": "target",
        "config_json": {"url": "/api/training/mock-printer/print", "method": "POST", "training_mock_printer": True},
    },
]


def json_flow_steps(pool_id_default: str = "POOL-001") -> list[dict[str, Any]]:
    return [
        {
            "id": "build_dnp_payload",
            "type": "build_json",
            "name": "Build DNP payload",
            "save_as": "target_payload",
            "template": {
                "pool_id": "{{request.body.pool_id}}",
                "order_id": "{{request.body.order_id}}",
                "inn": "{{request.body.inn}}",
                "product_code": "{{request.body.product_code}}",
                "codes": "{{request.body.codes}}",
                "training_default_pool": pool_id_default,
            },
        },
        {"id": "send_to_dnp", "type": "call_endpoint", "name": "Send to Training DNP", "connector": "Training DNP API", "method": "POST", "path": "/marking/pools", "body": "{{target_payload}}"},
        {"id": "return_dnp_response", "type": "return_response", "name": "Return DNP response", "body": "{{response}}"},
    ]


def two_odata_steps() -> list[dict[str, Any]]:
    return [
        {
            "id": "find_contractor",
            "type": "odata_query",
            "name": "Find contractor by INN",
            "connection": "Training OData ERP",
            "resource": "Catalog_Контрагенты",
            "filter_builder": [{"field": "ИНН", "operator": "eq", "value": "{{request.body.inn}}"}, {"field": "DeletionMark", "operator": "eq", "value": "false"}],
            "select": ["Ref_Key", "Description", "ИНН"],
            "top": 1,
            "save_as": "contractor",
            "required": True,
        },
        {
            "id": "find_product",
            "type": "odata_query",
            "name": "Find product by article",
            "connection": "Training OData ERP",
            "resource": "Catalog_Номенклатура",
            "filter_builder": [{"field": "Артикул", "operator": "eq", "value": "{{request.body.product_code}}"}, {"field": "DeletionMark", "operator": "eq", "value": "false"}],
            "select": ["Ref_Key", "Description", "Артикул", "GTIN"],
            "top": 1,
            "save_as": "product",
            "required": True,
        },
        {
            "id": "build_dnp_payload",
            "type": "build_json",
            "name": "Build target JSON",
            "save_as": "target_payload",
            "template": {
                "pool_id": "{{request.body.pool_id}}",
                "order_id": "{{request.body.order_id}}",
                "contractor": {"ref": "{{contractor.Ref_Key}}", "name": "{{contractor.Description}}", "inn": "{{contractor.ИНН}}"},
                "product": {"ref": "{{product.Ref_Key}}", "name": "{{product.Description}}", "article": "{{product.Артикул}}", "gtin": "{{product.GTIN}}"},
                "codes": "{{request.body.codes}}",
            },
        },
        {"id": "send_to_dnp", "type": "call_endpoint", "name": "Send to Training DNP", "connector": "Training DNP API", "method": "POST", "path": "/marking/pools", "body": "{{target_payload}}"},
        {"id": "return_dnp_response", "type": "return_response", "name": "Return response", "body": "{{response}}"},
    ]


def printer_steps() -> list[dict[str, Any]]:
    return [
        {
            "id": "build_print_job",
            "type": "build_json",
            "name": "Build print job",
            "save_as": "target_payload",
            "template": {
                "printer": "{{request.body.printer}}",
                "template": "{{request.body.template}}",
                "variables": "{{request.body.variables}}",
                "zpl": "^XA^FO40,40^A0N,32,32^FD{{request.body.variables.sscc}}^FS^XZ",
            },
        },
        {"id": "send_to_printer", "type": "call_endpoint", "name": "Send to Training Printer", "connector": "Training Printer", "method": "POST", "path": "/print", "body": "{{target_payload}}"},
        {"id": "return_printer_response", "type": "return_response", "name": "Return printer response", "body": "{{response}}"},
    ]


def xml_bridge_steps() -> list[dict[str, Any]]:
    return [
        {
            "id": "build_bridge_result",
            "type": "build_json",
            "name": "Preserve raw XML",
            "save_as": "target_payload",
            "template": {"status": "forwarded", "bridge": "training-xml-raw", "raw_xml": "{{request.xml}}"},
        },
        {"id": "return_xml_bridge_response", "type": "return_response", "name": "Return raw bridge response", "body": "{{target_payload}}"},
    ]


BASE_BODY = {
    "pool_id": "POOL-001",
    "order_id": "SO-1001",
    "inn": "7707083893",
    "product_code": "A-100",
    "codes": ["010464615169738421ABC", "010464615169738421DEF"],
}

XML_BODY = """<?xml version="1.0" encoding="UTF-8"?>
<Документ>
  <Номер>SO-1001</Номер>
  <ИНН>7707083893</ИНН>
  <Пул>POOL-001</Пул>
</Документ>"""

PRINT_BODY = {
    "printer": "TRAINING-PRINTER-01",
    "template": "pallet-label-v1",
    "variables": {"sscc": "046012345678901234", "order": "SO-1001"},
}

TRAINING_FLOWS: list[dict[str, Any]] = [
    {"name": "Training — 1C POST → DNP API", "slug": "training-onec-post-dnp", "description": "Smallest executable 1C JSON to DNP API lesson.", "target_type": "external_api", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_rest_api", "target_connector": "Training DNP API"}, "builder_json": {"steps": json_flow_steps()}, "test_payload_json": BASE_BODY},
    {"name": "Training — 1C POST → two OData lookups → JSON → DNP", "slug": "training-onec-two-odata-dnp", "description": "Golden scenario: 1C sends keys, OMH enriches with ERP OData and posts JSON to DNP.", "target_type": "external_api", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_rest_api", "target_connector": "Training DNP API"}, "builder_json": {"steps": two_odata_steps()}, "test_payload_json": BASE_BODY},
    {"name": "Training — 1C XML raw bridge", "slug": "training-onec-xml-raw-bridge", "description": "Raw XML preservation lesson.", "target_type": "internal", "endpoint": {"input_mode": "xml", "response_mode": "sync_response"}, "action_json": {"type": "create_event_only"}, "builder_json": {"steps": xml_bridge_steps()}, "test_payload_text": XML_BODY},
    {"name": "Training — 1C → printer", "slug": "training-onec-printer", "description": "1C print request to a mock printer.", "target_type": "printer", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_rest_api", "target_connector": "Training Printer"}, "builder_json": {"steps": printer_steps()}, "test_payload_json": PRINT_BODY},
    {"name": "Training — error: contractor not found", "slug": "training-error-contractor-not-found", "description": "Negative lesson: required OData lookup returns no contractor.", "target_type": "external_api", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_rest_api", "target_connector": "Training DNP API"}, "builder_json": {"steps": two_odata_steps()}, "test_payload_json": {**BASE_BODY, "inn": "9999999999"}},
    {"name": "Training — error: DNP API rejected pool", "slug": "training-error-dnp-rejected", "description": "Negative lesson: mock DNP rejects POOL-ERROR with external error details.", "target_type": "external_api", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_rest_api", "target_connector": "Training DNP API"}, "builder_json": {"steps": two_odata_steps()}, "test_payload_json": {**BASE_BODY, "pool_id": "POOL-ERROR"}},
    {"name": "Training — error: printer offline", "slug": "training-error-printer-offline", "description": "Negative lesson: mock printer returns offline error.", "target_type": "printer", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_rest_api", "target_connector": "Training Printer"}, "builder_json": {"steps": printer_steps()}, "test_payload_json": {**PRINT_BODY, "printer": "TRAINING-OFFLINE"}},
]

