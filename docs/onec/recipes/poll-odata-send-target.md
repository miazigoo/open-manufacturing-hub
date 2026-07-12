# OMH сам читает 1С OData по расписанию и отправляет данные во внешний сервис

Сценарий:

```text
OMH Scheduler
  -> 1C OData: Document_ЗаказКлиента
  -> Payload Builder
  -> External API / WMS
  -> Cursor update
  -> Run history
```

Используйте этот pattern, когда 1С не должна или не может сама отправлять POST в OMH, но внешний сервис должен получать новые или изменённые данные из 1С.

## Когда использовать polling

- 1С закрыта для доработок, но OData доступен на чтение.
- Нужно регулярно выгружать новые заказы, остатки, справочники или статусы.
- Внешний WMS/API принимает batch payload.
- Важна история запусков: что прочитали, что отправили, какой cursor был до и после.

Не используйте этот pattern как замену CDC, Kafka или универсальному ETL. В task 076 реализован один поток: `Scheduled OData Query -> Payload Builder -> Send Target Endpoint -> Cursor update -> Run history`.

## Открыть мастер

```text
/master?pattern=poll_odata_send_target
```

::open-page{route="/master?pattern=poll_odata_send_target" label="Открыть мастер polling OData -> target"}
::open-page{route="/polling" label="Открыть Polling Jobs и историю запусков"}

## OData filter

Пример для заказов клиентов:

```text
Connection: Training OData ERP или OData ERP
Resource: Document_ЗаказКлиента
Filter: Date ge datetime'{{cursor.last_success_at}}' and Posted eq true
Select: Ref_Key,Number,Date,Posted,Контрагент_Key
Top: 100
Pagination: enabled
Save as: orders
Required: false
```

Доступные переменные в polling filter:

```text
cursor.last_success_at
cursor.last_value
context.run_id
context.started_at
```

## Почему нужен cursor

Cursor/watermark защищает от повторной отправки одних и тех же данных. На первом запуске cursor пустой, поэтому нужно выбрать стратегию:

| Strategy | Что делает | Риск |
| --- | --- | --- |
| fixed_start_date | Подставляет дату, например `2026-01-01T00:00:00` | Можно пропустить старые данные до этой даты |
| last_n_hours | Берёт окно за последние N часов | Можно повторно отправить часть свежих данных |
| no_cursor_filter | Убирает cursor-условие и читает первые `$top` строк | Может отправить старые данные |

Обычно начинайте с `fixed_start_date`, выполните dry-run и проверьте sample rows.

## Payload

Payload сохраняется как `target_payload`.

```json
{
  "omh": {
    "run_id": "{{context.run_id}}",
    "event_type": "ODataPollingOrders",
    "source_system": "1C ERP",
    "target_system": "WMS"
  },
  "payload": {
    "orders": "{{orders}}",
    "cursor_from": "{{cursor.last_success_at}}",
    "count": "{{orders.length}}"
  }
}
```

`"{{orders}}"` сохраняет JSON array, а не строку. `orders.length` доступен для счётчиков.

## Target endpoint

```text
Method: POST
URL: http://wms.local/api/orders/import
Headers: {"Content-Type":"application/json"}
Body source: target_payload
Body type: JSON
Timeout: 30 sec
Empty result: do nothing and mark success
```

Training mock:

```text
POST /api/training/mock-wms/orders/import
```

Успешный ответ mock WMS:

```json
{
  "success": true,
  "accepted_count": 2,
  "status": "accepted"
}
```

## Manual test

Сначала запускайте Dry Run:

```text
query OData -> build payload -> do not send target -> do not update cursor
```

Потом Real send:

```text
query OData -> build payload -> send target
```

Checkbox `Обновить cursor после успешного теста` по умолчанию выключен. Включайте его только когда target response проверен.

## Save and enable

После сохранения создаются:

- disabled Polling Job;
- disabled IntegrationFlow artifact с builder_json;
- run history через `polling_job_runs`.

Дальше:

1. Запустите manual test.
2. Проверьте ответ WMS/API.
3. Откройте run history.
4. Включите расписание, если нужен interval run.

## Run history

В `/polling?jobId=<id>` проверьте:

- status;
- rows read;
- target sent;
- cursor before/after;
- OData request/response;
- target payload;
- target response;
- original error, если target вернул 4xx/5xx.

## Common errors

| Симптом | Что означает | Что проверить |
| --- | --- | --- |
| `1С не приняла логин или пароль` | OData auth failed | OData connection secret, пользователь 1С, права чтения |
| `Новых данных нет` | OData вернула пустой результат | Это success, если empty behavior не `mark_warning` |
| `Не удалось подставить cursor.last_success_at` | Cursor пустой и first-run strategy не закрыла filter | Fixed start date или last N hours |
| `Внешний API вернул ошибку` | Target 4xx/5xx или body `success=false` | Run details -> target_result; cursor не обновлён |
| `Внешний API не ответил за 30 секунд` | Timeout target | Доступность endpoint из backend-сети и timeout |

## Training example

```text
training.polling.odata_orders_to_wms
```

::example{exampleId="training.polling.odata_orders_to_wms"}
