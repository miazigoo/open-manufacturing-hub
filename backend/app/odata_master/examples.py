from __future__ import annotations

from app.odata_master.schemas import ODataMasterExample, ODataWizardSpec

DNP_CODE_SELECT = [
    "КодМаркировки",
    "ПолныйКодМаркировки",
    "ХешСуммаКодаМаркировки",
    "Статус",
    "Организация_Key",
    "СтанцияУправленияЗаказами_Key",
    "Номенклатура_Key",
    "Характеристика_Key",
    "ДатаЭмиссииУниверсальная",
    "ДатаПечатиУниверсальная",
    "ШтрихкодУпаковки_Key",
    "GTIN",
    "МаксимальнаяРозничнаяЦена",
    "СпособВводаВОборот",
    "Шаблон",
    "ХешСуммаУпаковки",
    "ТипШтрихкода",
    "МаркировкаОстатков",
    "СрокГодности",
    "ЗаказНаЭмиссию_Key",
    "ИдентификаторЗаказаСУЗ",
    "ИдентификаторБлокаСУЗ",
    "ВидКИЗ",
    "РазмерКИЗ",
    "ДокументОснование",
    "ДокументОснование_Type",
]

DNP_CHZ_CODE_POOL_SYNC = {
    "name": "DnP CHZ codes sync",
    "slug": "dnp_sinc_pull_codes",
    "description": "DnP запрашивает пул кодов Честного знака по номеру производственного заказа 1C.",
    "source": {
        "system": "dnp",
        "input_mode": "json",
        "sample": {
            "operation": "dnp_sinc_pull_codes",
            "sinc": "dnp_sinc_pull_codes",
            "order_id": 10271,
            "order_name": "26-0666/6938",
            "Number": "260666/6938",
        },
        "operation_key": {"field": "sinc", "value": "dnp_sinc_pull_codes"},
        "auth_mode": "none",
    },
    "steps": [
        {
            "type": "odata_query",
            "connection": "1C CHZ OData ERP",
            "resource": "Document_ЗаказНаПроизводство2_2",
            "filter": "Number eq '{{request.body.Number}}'",
            "select": ["Ref_Key", "Number", "Date", "Posted"],
            "top": 1,
            "save_as": "order",
            "required": True,
            "name": "Найти заказ производства",
        },
        {
            "type": "odata_object_query",
            "connection": "1C CHZ OData ERP",
            "base_resource": "Document_ЗаказНаПроизводство2_2",
            "object_key": "order.Ref_Key",
            "tabular_part": "Продукция",
            "select": ["Номенклатура_Key", "Количество", "КоличествоУпаковок"],
            "top": 100,
            "save_as": "products",
            "required": True,
            "name": "Прочитать продукцию заказа",
        },
        {
            "type": "foreach_odata",
            "items": "products",
            "item_as": "product",
            "connection": "1C CHZ OData ERP",
            "resource": "InformationRegister_ПулКодовМаркировкиСУЗ",
            "filter": "Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')",
            "select": DNP_CODE_SELECT,
            "top": 500,
            "paginate": True,
            "merge": "flatten",
            "save_as": "codes",
            "required": False,
            "name": "Найти коды по каждой строке продукции",
        },
    ],
    "final_action": {
        "type": "send_endpoint",
        "method": "POST",
        "url": "http://172.16.3.10/api/v2/integrations/omh/chz/codes/import",
        "body_type": "json",
        "body": {
            "omh": {
                "run_id": "{{context.run_id}}",
                "event_id": "{{context.event_id}}",
                "entity_id": "{{request.body.order_name}}",
                "event_type": "ChestniyZnakCodesSyncRequested",
                "entity_type": "DnPOrder",
                "source_system": "Open Manufacturing Hub",
                "target_system": "DnP",
                "correlation_id": "dnp-chz-sync:{{request.body.order_name}}",
            },
            "payload": {
                "rows": "{{codes}}",
                "order_id": "{{request.body.order_id}}",
                "odata_url": "http://172.16.3.19/erp_ptc/odata/standard.odata/InformationRegister_ПулКодовМаркировкиСУЗ",
                "order_name": "{{request.body.order_name}}",
                "onec_order_number": "{{order.Number}}",
                "order_numbers_by_basis": {"{{order.Ref_Key}}": "{{order.Number}}"},
            },
        },
        "response_to_caller": {"mode": "sync_response", "body_type": "json", "body": {"ok": True}},
    },
}

LOOKUP_JSON_RESPONSE = {
    "name": "Lookup order products",
    "slug": "lookup_order_products",
    "description": "Внешний API передает номер заказа, OMH читает 1C OData и возвращает JSON.",
    "source": {
        "system": "external_api",
        "input_mode": "json",
        "sample": {"operation": "lookup_order_products", "Number": "260666/6938", "device_type": "toodoo"},
        "operation_key": {"field": "operation", "value": "lookup_order_products"},
    },
    "steps": [
        {
            "type": "odata_query",
            "connection": "1C CHZ OData ERP",
            "resource": "Document_ЗаказНаПроизводство2_2",
            "filter": "Number eq '{{request.body.Number}}'",
            "select": ["Ref_Key", "Number", "Date", "Posted"],
            "top": 1,
            "save_as": "order",
            "required": True,
        },
        {
            "type": "odata_object_query",
            "connection": "1C CHZ OData ERP",
            "base_resource": "Document_ЗаказНаПроизводство2_2",
            "object_key": "order.Ref_Key",
            "tabular_part": "Продукция",
            "select": ["Номенклатура_Key", "Количество", "КоличествоУпаковок"],
            "top": 100,
            "save_as": "products",
            "required": True,
        },
    ],
    "final_action": {
        "type": "return_response",
        "response_to_caller": {
            "mode": "sync_response",
            "body_type": "json",
            "body": {"order": "{{order}}", "products": "{{products}}"},
        },
    },
}

LOOKUP_XML_RESPONSE = {
    **LOOKUP_JSON_RESPONSE,
    "name": "Lookup order products XML",
    "slug": "lookup_order_products_xml",
    "description": "Внешний API передает номер заказа, OMH читает 1C OData и возвращает XML.",
    "final_action": {
        "type": "return_response",
        "response_to_caller": {
            "mode": "sync_response",
            "body_type": "xml",
            "body": "<Response><OrderNumber>{{order.Number}}</OrderNumber><Rows>{{products}}</Rows></Response>",
        },
    },
}


def examples() -> list[ODataMasterExample]:
    return [
        ODataMasterExample(key="dnp_chz_code_pool_sync", title="DnP CHZ code pool sync", description="DnP -> OMH -> 1C OData -> коды Честного знака -> DnP", spec=ODataWizardSpec(**DNP_CHZ_CODE_POOL_SYNC)),
        ODataMasterExample(key="external_api_odata_json", title="External API -> OData -> JSON response", description="По номеру заказа вернуть JSON с заказом и продукцией.", spec=ODataWizardSpec(**LOOKUP_JSON_RESPONSE)),
        ODataMasterExample(key="external_api_odata_xml", title="External API -> OData -> XML response", description="По номеру заказа вернуть XML-ответ.", spec=ODataWizardSpec(**LOOKUP_XML_RESPONSE)),
    ]
