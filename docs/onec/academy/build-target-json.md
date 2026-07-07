# Собираем итоговый JSON в Step 3A

Этот урок относится к `/master` Step 3A. Его задача простая:

```text
Из request.body, order, products, codes и context собрать target_payload.
```

Step 3A не отправляет payload во внешний API. Он только строит тело и сохраняет его в draft как `build_payload`.

## Что должно быть готово

- Step 1 сохранил Input Contract.
- Step 2A нашел заказ и сохранил `order`.
- Step 2B прочитал табличную часть и сохранил `products`.
- Step 2C прошел по `products[]` и сохранил `codes`.

## Выбор формата

В блоке `Шаг 3A — Собираем итоговые данные` выберите `JSON`.

`save_as` оставьте `target_payload`.

## Режим таблицы

Для DnP используйте table mode:

```text
omh.run_id <- context.run_id
omh.event_id <- context.event_id
omh.entity_id <- request.body.order_name
omh.event_type <- ChestniyZnakCodesSyncRequested
omh.entity_type <- DnPOrder
omh.source_system <- Open Manufacturing Hub
omh.target_system <- DnP
omh.correlation_id <- dnp-chz-sync:{{request.body.order_name}}
payload.rows <- codes
payload.order_id <- request.body.order_id
payload.odata_url <- http://172.16.3.19/erp_ptc/odata/standard.odata/InformationRegister_ПулКодовМаркировкиСУЗ
payload.order_name <- request.body.order_name
payload.onec_order_number <- order.Number
```

Для `payload.rows` выберите type `array`, чтобы `codes` остался массивом.

## Dynamic Key

DnP example требует объект, где ключом является `order.Ref_Key`:

```json
{
  "payload": {
    "order_numbers_by_basis": {
      "<order.Ref_Key>": "<order.Number>"
    }
  }
}
```

В Dynamic keys задайте:

```text
object_path: payload.order_numbers_by_basis
key_source: order.Ref_Key
value_source: order.Number
```

## Raw JSON Template

Если нужна ручная структура, переключитесь в `Raw JSON template`:

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
    "order_name": "{{request.body.order_name}}",
    "onec_order_number": "{{order.Number}}",
    "order_numbers_by_basis": {
      "{{order.Ref_Key}}": "{{order.Number}}"
    }
  }
}
```

## Type-Preserving Rule

`"{{codes}}"` сохраняет массив.

`"{{order}}"` сохраняет объект.

`"dnp:{{request.body.order_name}}"` становится строкой.

Если preview пишет `VARIABLE_NOT_FOUND`, проверьте, что предыдущий шаг действительно сохранил переменную и в `$select` есть нужное поле.

## Что должно получиться

После Preview вы должны увидеть JSON с:

- `omh.run_id` и `omh.event_id`;
- `payload.rows` как массив codes;
- `payload.order_numbers_by_basis` с динамическим ключом `order.Ref_Key`;
- `payload.onec_order_number` из `order.Number`.
