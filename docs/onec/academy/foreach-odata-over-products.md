# Повторяем OData-запрос по каждой строке массива

Этот урок относится к `/master` Step 2C. Он отвечает на один вопрос:

```text
У меня есть products[]. Как для каждой строки выполнить OData-запрос и собрать общий codes[]?
```

## Исходные переменные

После Step 2A есть объект заказа:

```json
{
  "Ref_Key": "c3335ee4-43d0-11f1-8388-000c29b755c7",
  "Number": "260666/6938",
  "Date": "2026-04-29T16:38:53",
  "Posted": true
}
```

После Step 2B есть массив продукции:

```json
[
  {
    "Номенклатура_Key": "ff22288c-2da4-11f1-8388-000c29b755c7",
    "Количество": 180,
    "КоличествоУпаковок": 180
  }
]
```

В Step 2C OMH проходит по `products[]`. Одна строка массива называется `product`.

## Что настраиваем

В `/master` после сохранения Step 2B выберите:

```text
Шаг 2C — Повтор OData-запроса по массиву
```

Заполните поля:

```text
По какому массиву пройти: products
Как назвать одну строку массива: product
OData Resource: InformationRegister_ПулКодовМаркировкиСУЗ
Select: ПолныйКодМаркировки,ДокументОснование,Номенклатура_Key,Статус
$top: 500
Pagination: true
Merge: flatten
Save as: codes
Required: true
```

## Filter

Для DnP filter выглядит так:

```text
Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')
```

`{{product.Номенклатура_Key}}` берётся из текущей строки `products[]`.

`{{order.Ref_Key}}` берётся из результата Step 2A.

## Preview

Preview не выполняет запрос в 1С. Он берёт первую строку `products[]` и показывает rendered filter:

```text
Номенклатура_Key eq guid'ff22288c-2da4-11f1-8388-000c29b755c7' and ДокументОснование eq cast(guid'c3335ee4-43d0-11f1-8388-000c29b755c7', 'Document_ЗаказНаПроизводство2_2')
```

Если preview пишет, что `product.Номенклатура_Key` не найден, значит Step 2B не вернул это поле. Вернитесь к Step 2B и добавьте `Номенклатура_Key` в select.

## Test

Test выполняет вложенные OData-запросы в рамках `test_limit` и safety limits.

Ожидаемые метрики:

```text
source_count: 1
items_processed: 1
odata_requests: 1
rows_found: 180
```

Ожидаемый результат сохраняется как общий массив:

```text
codes[]
codes[0].ПолныйКодМаркировки
codes[0].Номенклатура_Key
```

## Merge modes

`flatten` — режим по умолчанию. Все строки из всех OData-ответов складываются в один массив `codes[]`. Для DnP это основной вариант.

`group_by_item` сохраняет группы по исходной строке `products[]`. Используйте для диагностики, когда нужно понять, какие коды пришли для какой продукции.

`first_per_item` берёт только первую найденную строку на каждый `product`.

## Safety limits

Foreach может случайно сделать много запросов в 1С, поэтому шаг хранит лимиты:

```text
max_items: 100
max_requests: 100
max_result_rows: 10000
```

Если `products[]` содержит больше строк, чем `max_requests`, validation остановит шаг до test. Это лучше, чем незаметно отправить сотни запросов в 1С.

## Частые ошибки

`Переменная order является объектом, а не массивом` — в поле source array выбран `order`. Для Step 2C нужен `products`.

`product.Номенклатура_Key не найдена` — Step 2B не вернул поле номенклатуры.

`$top не может быть больше 500` — поставьте `$top=500` и включите pagination.

`FOREACH_ODATA_RESULT_EMPTY` — 1С не вернула коды по фильтру. Проверьте `Номенклатура_Key`, `order.Ref_Key`, resource регистра и тип `ДокументОснование` в cast.

## Что не входит в Step 2C

- JSON builder;
- XML builder;
- endpoint send;
- сохранение полной интеграции;
- production queue;
- Timeline runtime;
- универсальный loop engine.
