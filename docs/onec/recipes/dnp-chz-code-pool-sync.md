# Рецепт: DnP CHZ code pool sync

Сценарий:

```text
DnP -> OMH -> 1C OData order -> tabular part Продукция -> foreach code pool -> DnP endpoint -> response
```

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

## Финальное действие

```text
POST http://172.16.3.10/api/v2/integrations/omh/chz/codes/import
```

Response to caller:

```json
{
  "ok": true
}
```

## Проверка

После сохранения endpoint будет:

```text
POST /api/bus/in/dnp_sinc_pull_codes
```

Откройте Timeline из ответа OMH и проверьте artifacts:

- `odata_query_request.json`
- `odata_query_response.json`
- `foreach_result.json`
- `outgoing_request.json`
- `return_response.json`
