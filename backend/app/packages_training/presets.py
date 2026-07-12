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
    "Document_ЗаказНаПроизводство2_2": [
        {"Ref_Key": "c3335ee4-43d0-11f1-8388-000c29b755c7", "Number": "260666/6938", "Date": "2026-04-29T16:38:53", "Posted": True, "DeletionMark": False},
    ],
    "Document_ЗаказНаПроизводство2_2(guid'c3335ee4-43d0-11f1-8388-000c29b755c7')/Продукция": [
        {"Номенклатура_Key": "ff22288c-2da4-11f1-8388-000c29b755c7", "Количество": 180, "КоличествоУпаковок": 180},
    ],
    "InformationRegister_ПулКодовМаркировкиСУЗ": [
        {"КодМаркировки": "CHZ-001", "ПолныйКодМаркировки": "0104607009529011215DnP001", "ХешСуммаКодаМаркировки": "hash-001", "Статус": "emitted", "Организация_Key": "org-001", "СтанцияУправленияЗаказами_Key": "suz-001", "Номенклатура_Key": "ff22288c-2da4-11f1-8388-000c29b755c7", "Характеристика_Key": "char-001", "ДатаЭмиссииУниверсальная": "2026-04-29T17:00:00", "ДатаПечатиУниверсальная": None, "ШтрихкодУпаковки_Key": "pack-001", "GTIN": "04607009529011", "МаксимальнаяРозничнаяЦена": 0, "СпособВводаВОборот": "Производство", "Шаблон": "default", "ХешСуммаУпаковки": "pack-hash-001", "ТипШтрихкода": "DataMatrix", "МаркировкаОстатков": False, "СрокГодности": "2027-04-29", "ЗаказНаЭмиссию_Key": "emission-001", "ИдентификаторЗаказаСУЗ": "SUZ-ORDER-001", "ИдентификаторБлокаСУЗ": "SUZ-BLOCK-001", "ВидКИЗ": "unit", "РазмерКИЗ": "standard", "ДокументОснование": "c3335ee4-43d0-11f1-8388-000c29b755c7", "ДокументОснование_Type": "Document_ЗаказНаПроизводство2_2"},
        {"КодМаркировки": "CHZ-002", "ПолныйКодМаркировки": "0104607009529011215DnP002", "ХешСуммаКодаМаркировки": "hash-002", "Статус": "emitted", "Организация_Key": "org-001", "СтанцияУправленияЗаказами_Key": "suz-001", "Номенклатура_Key": "ff22288c-2da4-11f1-8388-000c29b755c7", "Характеристика_Key": "char-001", "ДатаЭмиссииУниверсальная": "2026-04-29T17:01:00", "ДатаПечатиУниверсальная": None, "ШтрихкодУпаковки_Key": "pack-001", "GTIN": "04607009529011", "МаксимальнаяРозничнаяЦена": 0, "СпособВводаВОборот": "Производство", "Шаблон": "default", "ХешСуммаУпаковки": "pack-hash-002", "ТипШтрихкода": "DataMatrix", "МаркировкаОстатков": False, "СрокГодности": "2027-04-29", "ЗаказНаЭмиссию_Key": "emission-001", "ИдентификаторЗаказаСУЗ": "SUZ-ORDER-001", "ИдентификаторБлокаСУЗ": "SUZ-BLOCK-001", "ВидКИЗ": "unit", "РазмерКИЗ": "standard", "ДокументОснование": "c3335ee4-43d0-11f1-8388-000c29b755c7", "ДокументОснование_Type": "Document_ЗаказНаПроизводство2_2"},
        {"КодМаркировки": "CHZ-003", "ПолныйКодМаркировки": "0104607009529011215DnP003", "ХешСуммаКодаМаркировки": "hash-003", "Статус": "emitted", "Организация_Key": "org-001", "СтанцияУправленияЗаказами_Key": "suz-001", "Номенклатура_Key": "ff22288c-2da4-11f1-8388-000c29b755c7", "Характеристика_Key": "char-001", "ДатаЭмиссииУниверсальная": "2026-04-29T17:02:00", "ДатаПечатиУниверсальная": None, "ШтрихкодУпаковки_Key": "pack-001", "GTIN": "04607009529011", "МаксимальнаяРозничнаяЦена": 0, "СпособВводаВОборот": "Производство", "Шаблон": "default", "ХешСуммаУпаковки": "pack-hash-003", "ТипШтрихкода": "DataMatrix", "МаркировкаОстатков": False, "СрокГодности": "2027-04-29", "ЗаказНаЭмиссию_Key": "emission-001", "ИдентификаторЗаказаСУЗ": "SUZ-ORDER-001", "ИдентификаторБлокаСУЗ": "SUZ-BLOCK-001", "ВидКИЗ": "unit", "РазмерКИЗ": "standard", "ДокументОснование": "c3335ee4-43d0-11f1-8388-000c29b755c7", "ДокументОснование_Type": "Document_ЗаказНаПроизводство2_2"},
    ],
    "Document_ЗаказКлиента": [
        {"Ref_Key": "66666666-6666-6666-6666-666666666666", "Number": "260666/6938", "Date": "2026-07-12T12:00:00", "Posted": True, "Контрагент_Key": "11111111-1111-1111-1111-111111111111", "DeletionMark": False},
        {"Ref_Key": "44444444-4444-4444-4444-444444444444", "Number": "SO-1001", "Date": "2026-07-01T10:00:00", "Posted": True, "Контрагент_Key": "11111111-1111-1111-1111-111111111111", "DeletionMark": False},
        {"Ref_Key": "55555555-5555-5555-5555-555555555555", "Number": "SO-1002", "Date": "2026-07-02T11:30:00", "Posted": False, "Контрагент_Key": "22222222-2222-2222-2222-222222222222", "DeletionMark": False},
    ],
    "Document_ЗаказКлиента(guid'66666666-6666-6666-6666-666666666666')/Товары": [
        {"Номенклатура_Key": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "Количество": 2, "Цена": 120.5, "Сумма": 241.0},
        {"Номенклатура_Key": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "Количество": 1, "Цена": 77.0, "Сумма": 77.0},
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
        "name": "Training External API",
        "connector_type": "rest",
        "direction": "target",
        "config_json": {"url": "/api/training/mock-external-api/orders/import", "method": "POST", "training_mock_external_api": True},
    },
    {
        "name": "Training Site API",
        "connector_type": "rest",
        "direction": "target",
        "config_json": {"url": "/api/training/mock-site/orders/import", "method": "POST", "training_mock_site": True},
    },
    {
        "name": "Training 1C HTTP Service",
        "connector_type": "rest",
        "direction": "target",
        "config_json": {
            "url": "/api/training/mock-onec/hs/omh/order-external-id",
            "method": "POST",
            "training_mock_onec_writeback": True,
            "training_mock_onec_shipment_facts": True,
        },
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


def print_labels_steps() -> list[dict[str, Any]]:
    return [
        {
            "id": "print_labels",
            "type": "print_labels",
            "name": "Render ZPL and send to Training Printer",
            "printer_selection": {"mode": "from_request", "path": "request.body.printer", "fixed_printer_name": "TRAINING-PRINTER-01"},
            "labels": {"path": "request.body.labels", "item_as": "label", "required_fields": ["code"], "optional_fields": ["sku", "title", "qty", "sequence_no"]},
            "zpl_template": "^XA\n^CI28\n^FO30,30^A0N,30,30^FD{{label.title}}^FS\n^FO30,70^A0N,24,24^FDSKU: {{label.sku}}^FS\n^FO30,110^BXN,5,200^FD{{label.code}}^FS\n^FO30,300^A0N,24,24^FD#{{label.sequence_no}} / {{request.body.job_key}}^FS\n^XZ",
            "print_mode": "dry_run",
            "save_as": "print_status",
        },
        {"id": "return_print_status", "type": "return_response", "name": "Return print status", "body": "{{print_status}}"},
    ]


def xml_bridge_steps() -> list[dict[str, Any]]:
    return [
        {
            "id": "raw_xml_forward",
            "type": "raw_xml_forward",
            "name": "Forward XML unchanged to Training 1C",
            "source": "request.xml",
            "method": "POST",
            "url": "http://training.local/hs/omh/receive-upd-xml",
            "path": "/receive-upd-xml",
            "headers": {"Content-Type": "application/xml; charset=utf-8"},
            "timeout_seconds": 30,
            "require_valid_xml": True,
            "verify_hash": True,
            "save_response_as": "target_response",
            "training_mock_onec_xml_receiver": True,
        },
        {"id": "return_xml_bridge_response", "type": "return_response", "name": "Return raw bridge response", "body": "{{target_response}}"},
    ]


def xml_odata_response_steps() -> list[dict[str, Any]]:
    return [
        {
            "id": "extract_xml_fields",
            "type": "xml_extract",
            "name": "Extract order number from XML",
            "source": "request.xml",
            "raw_artifact_name": "raw_xml_input.xml",
            "fields": [
                {"name": "operation", "path": "/Request/Operation", "required": True},
                {"name": "order_number", "path": "/Request/Number", "required": True},
                {"name": "format", "path": "/Request/Format", "required": False},
            ],
        },
        {
            "id": "query_odata",
            "type": "odata_query",
            "name": "Find customer order",
            "connection": "Training OData ERP",
            "resource": "Document_ЗаказКлиента",
            "filter": "Number eq '{{order_number}}'",
            "select": ["Ref_Key", "Number", "Date", "Posted"],
            "top": 1,
            "paginate": False,
            "save_as": "order",
            "required": True,
        },
        {
            "id": "build_response",
            "type": "build_payload",
            "name": "Build XML response",
            "body_type": "xml",
            "save_as": "target_payload",
            "json_mode": "raw_template",
            "response_artifacts": True,
            "template": """<Response>
  <Success>true</Success>
  <Order>
    <UUID>{{order.Ref_Key}}</UUID>
    <Number>{{order.Number}}</Number>
    <Date>{{order.Date}}</Date>
    <Posted>{{order.Posted}}</Posted>
  </Order>
</Response>""",
        },
        {
            "id": "return_xml_response",
            "type": "return_response",
            "name": "Return XML response",
            "response_body_type": "xml",
            "status_code": 200,
            "headers": {"Content-Type": "application/xml; charset=utf-8"},
            "body_template": "{{target_payload}}",
        },
    ]


def order_xml_response_steps() -> list[dict[str, Any]]:
    return [
        {
            "id": "find_order",
            "type": "odata_query",
            "name": "Find customer order",
            "connection": "Training OData ERP",
            "resource": "Document_ЗаказКлиента",
            "filter": "Number eq '{{request.body.number}}'",
            "select": ["Ref_Key", "Number", "Date", "Posted"],
            "top": 1,
            "paginate": False,
            "save_as": "order",
            "required": True,
        },
        {
            "id": "read_items",
            "type": "odata_query",
            "name": "Read customer order items",
            "connection": "Training OData ERP",
            "resource": "Document_ЗаказКлиента(guid'{{order.Ref_Key}}')/Товары",
            "select": ["Номенклатура_Key", "Количество", "Цена", "Сумма"],
            "top": 100,
            "paginate": False,
            "save_as": "items",
            "required": True,
            "source_master_type": "odata_object_query",
            "object_variable": "order",
            "nested_resource": "Товары",
        },
        {
            "id": "build_xml_response",
            "type": "build_payload",
            "name": "Build XML response",
            "body_type": "xml",
            "save_as": "target_payload",
            "json_mode": "raw_template",
            "template": """<Response>
  <Success>true</Success>
  <Order>
    <UUID>{{order.Ref_Key}}</UUID>
    <Number>{{order.Number}}</Number>
    <Date>{{order.Date}}</Date>
    <Posted>{{order.Posted}}</Posted>
  </Order>
  <Items>
    {{#items}}
    <Item>
      <ProductUUID>{{Номенклатура_Key}}</ProductUUID>
      <Quantity>{{Количество}}</Quantity>
      <Price>{{Цена}}</Price>
      <Amount>{{Сумма}}</Amount>
    </Item>
    {{/items}}
  </Items>
</Response>""",
        },
        {
            "id": "return_xml_response",
            "type": "return_response",
            "name": "Return XML response",
            "response_body_type": "xml",
            "status_code": 200,
            "headers": {"Content-Type": "application/xml; charset=utf-8"},
            "body_template": "{{target_payload}}",
        },
    ]


def wms_shipment_fact_steps() -> list[dict[str, Any]]:
    return [
        {
            "id": "find_order",
            "type": "odata_query",
            "name": "Find customer order",
            "connection": "Training OData ERP",
            "resource": "Document_ЗаказКлиента",
            "filter": "Number eq '{{request.body.order_number}}'",
            "select": ["Ref_Key", "Number", "Date", "Posted"],
            "top": 1,
            "paginate": False,
            "save_as": "order",
            "required": True,
        },
        {
            "id": "build_onec_payload",
            "type": "build_payload",
            "name": "Build 1C shipment fact payload",
            "body_type": "json",
            "save_as": "onec_payload",
            "json_mode": "raw_template",
            "template": {
                "omh": {
                    "event_id": "{{context.event_id}}",
                    "run_id": "{{context.run_id}}",
                    "correlation_id": "wms-shipment:{{request.body.wms_shipment_id}}",
                    "event_type": "WmsShipmentFactReceived",
                    "entity_type": "ShipmentFact",
                    "entity_id": "{{request.body.wms_shipment_id}}",
                    "source_system": "WMS",
                    "target_system": "1C ERP",
                },
                "payload": {
                    "order_ref_key": "{{order.Ref_Key}}",
                    "order_number": "{{request.body.order_number}}",
                    "wms_shipment_id": "{{request.body.wms_shipment_id}}",
                    "status": "{{request.body.status}}",
                    "warehouse_code": "{{request.body.warehouse_code}}",
                    "shipped_at": "{{request.body.shipped_at}}",
                    "items": "{{request.body.items}}",
                },
            },
        },
        {
            "id": "send_onec_http_service",
            "type": "call_endpoint",
            "name": "Send shipment fact to Training 1C HTTP Service",
            "connector": "Training 1C HTTP Service",
            "method": "POST",
            "path": "/shipment-facts",
            "body": "{{onec_payload}}",
            "body_type": "json",
            "save_response_as": "onec_response",
        },
        {
            "id": "return_wms_response",
            "type": "return_response",
            "name": "Return 1C response to WMS",
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": {
                "success": "{{onec_response.success}}",
                "wms_shipment_id": "{{request.body.wms_shipment_id}}",
                "order_number": "{{request.body.order_number}}",
                "onec_response": "{{onec_response}}",
            },
        },
    ]


BASE_BODY = {
    "pool_id": "POOL-001",
    "order_id": "SO-1001",
    "inn": "7707083893",
    "product_code": "A-100",
    "codes": ["010464615169738421ABC", "010464615169738421DEF"],
}

LOOKUP_ORDER_BODY = {
    "operation": "lookup_order_products",
    "number": "260666/6938",
    "format": "xml",
}

XML_LOOKUP_ORDER_BODY = """<Request>
  <Operation>lookup_order</Operation>
  <Number>260666/6938</Number>
  <Format>xml</Format>
</Request>"""

WMS_SHIPMENT_FACT_BODY = {
    "operation": "shipment_fact",
    "wms_shipment_id": "WMS-SHIP-123",
    "order_number": "260666/6938",
    "status": "shipped",
    "warehouse_code": "MAIN",
    "shipped_at": "2026-07-04T14:30:00",
    "items": [{"sku": "ABC-123", "qty": 10, "barcode": "04646151697384"}],
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

PRINT_LABELS_BODY = {
    "operation": "print_labels",
    "printer": "TRAINING-PRINTER-01",
    "job_key": "ORDER-123",
    "labels": [
        {"sequence_no": 1, "sku": "ABC-123", "title": "Плата ABC", "code": "010464615169738421ABC", "qty": 1},
        {"sequence_no": 2, "sku": "XYZ-777", "title": "Модуль XYZ", "code": "010464615169738421XYZ", "qty": 1},
    ],
}

TRAINING_FLOWS: list[dict[str, Any]] = [
    {"name": "Training — 1C POST → DNP API", "slug": "training-onec-post-dnp", "description": "Smallest executable 1C JSON to DNP API lesson.", "target_type": "external_api", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_rest_api", "target_connector": "Training DNP API"}, "builder_json": {"steps": json_flow_steps()}, "test_payload_json": BASE_BODY},
    {"name": "Training — 1C POST → two OData lookups → JSON → DNP", "slug": "training-onec-two-odata-dnp", "description": "Golden scenario: 1C sends keys, OMH enriches with ERP OData and posts JSON to DNP.", "target_type": "external_api", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_rest_api", "target_connector": "Training DNP API"}, "builder_json": {"steps": two_odata_steps()}, "test_payload_json": BASE_BODY},
    {"name": "Training — External API asks 1C order XML response", "slug": "training-onec-lookup-order-products-xml", "description": "External API asks for order products, OMH reads order/items from OData and returns XML.", "target_type": "external_api", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "return_response"}, "builder_json": {"steps": order_xml_response_steps()}, "test_payload_json": LOOKUP_ORDER_BODY},
    {"name": "Training — XML request → OData order → XML response", "slug": "training-onec-xml-lookup-order-response", "description": "External XML caller sends an order number, OMH extracts it, reads ERP OData and returns XML.", "target_type": "internal", "endpoint": {"input_mode": "xml", "response_mode": "sync_response"}, "action_json": {"type": "return_response", "operation": "xml_odata_xml_response"}, "builder_json": {"steps": xml_odata_response_steps()}, "test_payload_text": XML_LOOKUP_ORDER_BODY},
    {"name": "Training — WMS shipment fact → 1C HTTP Service", "slug": "training-wms-shipment-fact-to-onec", "description": "WMS sends shipment fact, OMH finds the order and calls the Training 1C HTTP service.", "source_type": "wms", "target_type": "onec", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_1c_http_service", "target_connector": "Training 1C HTTP Service", "operation": "update_shipment_status"}, "builder_json": {"steps": wms_shipment_fact_steps()}, "test_payload_json": WMS_SHIPMENT_FACT_BODY},
    {"name": "Training — 1C XML raw bridge", "slug": "training-onec-xml-raw-bridge", "description": "Raw XML preservation lesson.", "target_type": "onec", "endpoint": {"input_mode": "xml", "response_mode": "sync_response"}, "action_json": {"type": "call_1c_http_service", "operation": "receive_upd_xml", "business_object": "training-onec-xml-raw-bridge", "method": "POST", "url": "http://training.local/hs/omh/receive-upd-xml", "path": "/receive-upd-xml", "body_mode": "xml", "response_mode": "sync_response"}, "builder_json": {"steps": xml_bridge_steps()}, "test_payload_text": XML_BODY},
    {"name": "Training — 1C → printer", "slug": "training-onec-printer", "description": "1C print request to a mock printer.", "target_type": "printer", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_rest_api", "target_connector": "Training Printer"}, "builder_json": {"steps": printer_steps()}, "test_payload_json": PRINT_BODY},
    {"name": "Training — request → ZPL labels → printer", "slug": "training-print-labels", "description": "Request -> Printer wizard lesson: render ZPL labels[] and return normalized print status.", "target_type": "printer", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "return_response", "operation": "request_print"}, "builder_json": {"steps": print_labels_steps()}, "test_payload_json": PRINT_LABELS_BODY},
    {"name": "Training — error: contractor not found", "slug": "training-error-contractor-not-found", "description": "Negative lesson: required OData lookup returns no contractor.", "target_type": "external_api", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_rest_api", "target_connector": "Training DNP API"}, "builder_json": {"steps": two_odata_steps()}, "test_payload_json": {**BASE_BODY, "inn": "9999999999"}},
    {"name": "Training — error: DNP API rejected pool", "slug": "training-error-dnp-rejected", "description": "Negative lesson: mock DNP rejects POOL-ERROR with external error details.", "target_type": "external_api", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_rest_api", "target_connector": "Training DNP API"}, "builder_json": {"steps": two_odata_steps()}, "test_payload_json": {**BASE_BODY, "pool_id": "POOL-ERROR"}},
    {"name": "Training — error: printer offline", "slug": "training-error-printer-offline", "description": "Negative lesson: mock printer returns offline error.", "target_type": "printer", "endpoint": {"input_mode": "json", "response_mode": "sync_response"}, "action_json": {"type": "call_rest_api", "target_connector": "Training Printer"}, "builder_json": {"steps": printer_steps()}, "test_payload_json": {**PRINT_BODY, "printer": "TRAINING-OFFLINE"}},
]
