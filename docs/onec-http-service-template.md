# 1C HTTP Service Template for OMH

This document describes the recommended custom 1C HTTP service contract for Open Manufacturing Hub. OMH treats 1C as a configurable HTTP target. No COM, direct SQL, SOAP or generated 1C extension is required for this template.

## Recommended Endpoints

```text
GET  /hs/omh/health
POST /hs/omh/events
POST /hs/omh/shipment-facts
POST /hs/omh/stock-balances
POST /hs/omh/inventory-results
```

## Standard Request Envelope

OMH sends business payloads in a stable envelope. The `omh` block is operational metadata for traceability. The `payload` block is the business document/fact.

```json
{
  "omh": {
    "event_id": "evt_uuid",
    "run_id": "run_uuid",
    "correlation_id": "corr_777",
    "event_type": "ShipmentFactCreated",
    "entity_type": "ShipmentFact",
    "entity_id": "WMS-SHIP-1532",
    "source_system": "Mock WMS",
    "target_system": "1C ERP",
    "sent_at": "2026-07-02T14:30:00Z"
  },
  "payload": {
    "external_order_id": "1532",
    "shipment_id": "WMS-SHIP-1532",
    "status": "shipped",
    "items": [
      {"sku": "ABC123", "quantity": 5}
    ]
  }
}
```

## Standard Success Response

```json
{
  "success": true,
  "external_document_id": "1C-DOC-000123",
  "status": "accepted",
  "message": "Shipment fact accepted"
}
```

## Standard Failure Response

Return HTTP `200` for business failures that were handled by 1C. OMH will mark the connector call as failed when `success=false`.

```json
{
  "success": false,
  "error_code": "ORDER_NOT_FOUND",
  "error_message": "Order 1532 was not found in 1C",
  "details": {"order_id": "1532"}
}
```

Use HTTP `5xx` only for technical failures where the 1C service could not process the request.

## Operation Presets

OMH supports these operation names by default:

```json
{
  "update_shipment_status": {"method": "POST", "path": "/shipment-facts"},
  "update_stock_balance": {"method": "POST", "path": "/stock-balances"},
  "send_inventory_result": {"method": "POST", "path": "/inventory-results"},
  "send_movement_fact": {"method": "POST", "path": "/movements"}
}
```

A connector instance can override paths with `config_json.operations`.

## 1C Pseudo-Code

```1c
Функция ОбработатьФактОтгрузки(Запрос)
    Тело = Запрос.ПолучитьТелоКакСтроку();
    Данные = ПрочитатьJSON(Тело);

    НомерЗаказа = Данные.payload.external_order_id;

    Если Не НайтиЗаказ(НомерЗаказа) Тогда
        Возврат ОтветJSON(Ложь, "ORDER_NOT_FOUND", "Заказ не найден");
    КонецЕсли;

    // Найти заказ клиента / реализацию / документ-основание.
    // Обновить статус или создать документ фактической отгрузки.
    // Записать внешний идентификатор OMH для идемпотентности.

    Возврат ОтветJSON(Истина, "", "Факт отгрузки принят");
КонецФункции

Функция ОтветJSON(Успех, КодОшибки, Сообщение)
    Ответ = Новый Структура;
    Ответ.Вставить("success", Успех);

    Если Успех Тогда
        Ответ.Вставить("status", "accepted");
        Ответ.Вставить("external_document_id", "1C-DOC-000123");
        Ответ.Вставить("message", Сообщение);
    Иначе
        Ответ.Вставить("error_code", КодОшибки);
        Ответ.Вставить("error_message", Сообщение);
    КонецЕсли;

    Возврат ЗаписатьJSON(Ответ);
КонецФункции
```
