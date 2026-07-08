# Рецепт: DnP CHZ code pool sync

Сценарий:

```text
DnP -> OMH -> 1C OData order -> tabular part Продукция -> foreach code pool -> build target_payload
```

Endpoint send to DnP and caller response are configured in current Step 4A. Full production publish/runtime queue remains a later stage.

## Входящий JSON

```json
{
  "operation": "dnp_sinc_pull_codes",
  "sinc": "dnp_sinc_pull_codes",
  "order_id": 10271,
  "order_name": "26-0666/6938",
  "Number": "260666/6938"
}
```

## OData steps

### 1. Найти заказ производства

```text
Resource: Document_ЗаказНаПроизводство2_2
Filter: Number eq '{{request.body.Number}}'
Select: Ref_Key,Number,Date,Posted
Top: 1
Save as: order
```

### 2. Прочитать продукцию

```text
Resource: Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция
Select: Номенклатура_Key,Количество,КоличествоУпаковок
Top: 100
Save as: products
```

### 3. Повторить OData по products

```text
Source array: products
Item name: product
Resource: InformationRegister_ПулКодовМаркировкиСУЗ
Filter: Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')
Top: 500
Pagination: enabled
Merge: flatten
Save as: codes
```

## Step 3A. Собрать JSON payload

Выберите `/master` блок `Шаг 3A — Собираем итоговые данные`.

```text
Body type: JSON
Save as: target_payload
```

DnP JSON:

```json
{
  "omh": {
    "run_id": "{{context.run_id}}",
    "event_id": "{{context.event_id}}",
    "entity_id": "{{request.body.order_name}}",
    "event_type": "ChestniyZnakCodesSyncRequested",
    "entity_type": "DnPOrder",
    "source_system": "Open Manufacturing Hub",
    "target_system": "DnP",
    "correlation_id": "dnp-chz-sync:{{request.body.order_name}}"
  },
  "payload": {
    "rows": "{{codes}}",
    "order_id": "{{request.body.order_id}}",
    "odata_url": "http://172.16.3.19/erp_ptc/odata/standard.odata/InformationRegister_ПулКодовМаркировкиСУЗ",
    "order_name": "{{request.body.order_name}}",
    "onec_order_number": "{{order.Number}}",
    "order_numbers_by_basis": {
      "{{order.Ref_Key}}": "{{order.Number}}"
    }
  }
}
```

Rules:

- `"{{codes}}"` keeps `codes` as JSON array.
- `{{order.Ref_Key}}` in object key renders dynamic JSON key.
- `codes.length` is available for counters.
- Missing path returns `VARIABLE_NOT_FOUND`.

## Step 4A. Финальное действие

```text
Action type: send_endpoint
Method: POST
POST http://172.16.3.10/api/v2/integrations/omh/chz/codes/import
```

Body source:

```text
target_payload
```

Expected response to caller after future send stage:

```json
{
  "ok": true
}
```

Проверка:

- `Preview final action` не отправляет запрос в DnP.
- `Dry run` не ходит в сеть и показывает `would_send`.
- `Real test endpoint` отправляет настоящий HTTP-запрос только после подтверждения в UI.
- Private URL `172.16.*` разрешен, но preview покажет warning про доступность из backend-контейнера.

## Проверка текущего Step 3A

Нажмите `Preview payload` и проверьте:

- `payload.rows` is an array, not a string.
- `payload.order_numbers_by_basis` has key equal to `order.Ref_Key`.
- `omh.correlation_id` contains `request.body.order_name`.

## Проверка будущего full flow

После реализации final action endpoint будет:

```text
POST /api/bus/in/dnp_sinc_pull_codes
```

Откройте Timeline из ответа OMH и проверьте artifacts:

- `odata_query_request.json`
- `odata_query_response.json`
- `foreach_result.json`
- `target_payload.json`
- `outgoing_request.json`
- `return_response.json`
