# Рецепт: загрузка упакованных кодов ЧЗ из DnP в 1C

## Когда использовать

Оператор в 1C заполняет документ `Нанесение и ввод в оборот`. Раньше он вручную
брал txt-файл из DnP и вставлял данные в документ. Теперь 1C может запросить те
же данные у OMH одним HTTP-запросом, а OMH заберет их из DnP.

```text
1C -> OMH: дай коды по заказу и дате
OMH -> DnP: дай коды по заказу и дате
DnP -> OMH: JSON с кодами и агрегатами
OMH -> 1C: JSON с кодами и агрегатами
```

## Endpoint OMH

```http
POST /api/chz-aggregations/pull-from-dnp
Content-Type: application/json
```

Запрос:

```json
{
  "order_number_1c": "260530/6543",
  "date_from": "2026-07-13",
  "date_to": "2026-07-13",
  "only_new": true
}
```

- `order_number_1c` - обязательный номер заказа в формате 1C.
- `date_from` / `date_to` - необязательный период закрытия коробок.
- `only_new` - по умолчанию `true`, исключает строки, которые DnP уже выгружал
  в 1C ранее.

Ответ:

```json
{
  "ok": true,
  "order_number_1c": "260530/6543",
  "order_name_dnp": "26-0530/6543",
  "codes_count": 2481,
  "boxes_count": 276,
  "tsv_text_base64": "...",
  "rows": [
    { "full_code_base64": "...", "sscc": "00046306261900000012" }
  ],
  "event_id": "uuid",
  "timeline_url": "/events/uuid"
}
```

- `full_code_base64` - полный GS1-код с настоящим ASCII 29 в Base64.
- `tsv_text_base64` - совместимый формат для старого механизма загрузки из
  внешнего файла: `<полный код с настоящим GS><TAB><SSCC>` на каждой строке.
- `event_id` / `timeline_url` - ссылка на событие OMH, чтобы видеть, что именно
  запрашивалось и что ответил DnP.

## Важные правила

- OMH всегда вызывает DnP с `mark_exported: false`. DnP помечает строки как
  выгруженные только после того, как 1C реально вставила данные в документ.
  Поэтому запрос можно безопасно повторять.
- Таймаут на запрос: `CHZ_DNP_PACKED_CODES_TIMEOUT_SECONDS` (по умолчанию 180
  секунд). В 1C на этот вызов стоит держать таймаут 180-300 секунд.

## Настройка

Переменные окружения backend или переменные текущего environment в UI
(`Settings -> Environments -> Variables`, ключи без префикса `OMH_`):

```bash
OMH_CHZ_DNP_PACKED_CODES_EXPORT_URL=http://<dnp-host>/api/v2/integrations/omh/chz/packed-codes/export-for-1c
OMH_CHZ_DNP_PACKED_CODES_TIMEOUT_SECONDS=180
```

## Проверка без 1C

На странице `Пулы кодов ЧЗ` есть вкладка `Загрузка в 1С (из DnP)`: укажите
заказ и даты, нажмите `Получить коды из DnP`, проверьте счетчики и скачайте
TSV. Тот же запрос виден в Timeline по ссылке из результата.
