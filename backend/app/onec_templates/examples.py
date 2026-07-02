HTTP_ENDPOINTS = [
    {"method": "GET", "path": "/hs/omh/health", "description": "Readiness check for OMH before sending business events."},
    {"method": "POST", "path": "/hs/omh/events", "description": "Generic business event intake."},
    {"method": "POST", "path": "/hs/omh/shipment-facts", "description": "Shipment fact or status update from WMS."},
    {"method": "POST", "path": "/hs/omh/stock-balances", "description": "Stock balance snapshot update."},
    {"method": "POST", "path": "/hs/omh/inventory-results", "description": "Inventory result update."},
]

REQUEST_ENVELOPE = {
    "omh": {
        "event_id": "evt_uuid",
        "run_id": "run_uuid",
        "correlation_id": "corr_777",
        "event_type": "ShipmentFactCreated",
        "entity_type": "ShipmentFact",
        "entity_id": "WMS-SHIP-1532",
        "source_system": "Mock WMS",
        "target_system": "1C ERP",
        "sent_at": "2026-07-02T14:30:00Z",
    },
    "payload": {
        "external_order_id": "1532",
        "shipment_id": "WMS-SHIP-1532",
        "status": "shipped",
        "items": [{"sku": "ABC123", "quantity": 5}],
    },
}

SUCCESS_RESPONSE = {"success": True, "external_document_id": "1C-DOC-000123", "status": "accepted", "message": "Shipment fact accepted"}
FAILURE_RESPONSE = {"success": False, "error_code": "ORDER_NOT_FOUND", "error_message": "Order 1532 was not found in 1C", "details": {"order_id": "1532"}}

PSEUDO_CODE = """Функция ОбработатьФактОтгрузки(Запрос)
    Тело = Запрос.ПолучитьТелоКакСтроку();
    Данные = ПрочитатьJSON(Тело);

    НомерЗаказа = Данные.payload.external_order_id;

    Если Не НайтиЗаказ(НомерЗаказа) Тогда
        Возврат ОтветJSON(Ложь, "ORDER_NOT_FOUND", "Заказ не найден");
    КонецЕсли;

    // Обновить статус / создать документ реализации / записать факт отгрузки.

    Возврат ОтветJSON(Истина, "", "Факт отгрузки принят");
КонецФункции"""
