# Рецепт: внешний сервис отправляет агрегацию ЧЗ в 1C

## Когда использовать

Внешний сервис, лазерная станция или учетная система присылает файл/JSON с уже
агрегированными кодами маркировки. OMH принимает эти данные, проверяет формат,
группирует коды по агрегату и отправляет подготовленный payload в HTTP-сервис 1C.

## Формат CSV

Файл без заголовка. В каждой строке две колонки, разделитель - TAB:

```text
<полный код маркировки с настоящим GS><TAB><код агрегата>
```

Важно: GS-разделитель остается настоящим ASCII 29 внутри полного кода. OMH не
делит файл через обычный `splitlines`, потому что GS тоже является управляющим
символом. Парсер режет строки только по `\n`.

## Endpoint

Preview без отправки в 1C:

```http
POST /api/chz-aggregations/register-file/preview
Content-Type: multipart/form-data
```

Боевая отправка в 1C:

```http
POST /api/chz-aggregations/register-file
Content-Type: multipart/form-data
```

Поля формы:

- `file` - CSV/TXT файл.
- `order_number` - необязательно, если номер заказа есть в имени файла.
- `source_system` - необязательно.
- `source_document_id` - необязательно.

Если имя файла похоже на `chz-packed-codes-26-0530_6543-2026-05-13.csv`, OMH
получит:

- `order_number_1c`: `260530/6543`
- `order_number_external`: `26-0530/6543`

## Payload в 1C

OMH отправляет в 1C JSON. Полные коды идут как Base64, чтобы не потерять GS:

```json
{
  "omh": {
    "event_type": "ChestniyZnakAggregationCodesReceived",
    "entity_type": "ChzAggregationRegistration"
  },
  "payload": {
    "order_number_1c": "260530/6543",
    "order_number_external": "26-0530/6543",
    "total_codes": 2481,
    "total_aggregates": 276,
    "aggregates": [
      {
        "aggregate_code": "00046306261900008223",
        "codes_count": 9,
        "full_codes_base64": ["..."]
      }
    ]
  }
}
```

## Настройка в UI

Откройте:

```text
Пулы кодов ЧЗ -> Агрегация -> 1С
```

На вкладке можно:

- задать URL HTTP-сервиса 1C;
- задать timeout и token;
- загрузить CSV для preview;
- отправить файл в 1C;
- посмотреть журнал последних отправок.

## Что проверять

- `total_codes` должен совпасть с количеством строк файла.
- `total_aggregates` должен совпасть с количеством уникальных агрегатов.
- `duplicate_codes` должен быть `0`.
- В sample GS отображается как `<GS>`, но в payload для 1C код передается Base64.

## Следующий шаг в 1C

В 1C нужно сделать HTTP-сервис, который принимает этот payload, декодирует
`full_codes_base64`, находит заказ эмиссии/производственный документ и регистрирует
агрегацию кодов штатным способом 1C.
