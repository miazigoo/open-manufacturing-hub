# Рецепт: 1C отправляет пул кодов ЧЗ в OMH

## Когда использовать

1C уже получила пул кодов от ГИС МТ и должна передать его дальше. OMH принимает
пул один раз и выполняет два действия:

- сохраняет файл для лазера в настроенную SMB-папку;
- отправляет этот же пул в DnP, чтобы DnP не читал 1C OData.

## Endpoint

```text
POST /api/bus/in/onec-chz-pool-delivery
Content-Type: application/json
```

Это стабильный endpoint для текущей 1C-интеграции. При переходе от ручной
кнопки к автоматической отправке в 1C менять ссылку не нужно: меняется только
момент вызова.

## Payload из 1C

```json
{
  "order_number": "260703/5442",
  "source_document_id": "AEAE-000137",
  "source_document_name": "Заказ на эмиссию кодов маркировки AEAE-000137",
  "full_codes_base64": [
    "MDEwNDY0NjE1MTY5NzE4NjIxNV88cWxrPFpiQ1dGUD5XMilmb1UdOTNsemhV"
  ]
}
```

`full_codes_base64` - production-поле. В него 1C кладет `ПолныйКодМаркировки`
как Base64. OMH не теряет настоящий GS-разделитель ASCII 29 и передает пул
дальше без ручной сборки кода.

## Ответ для 1C

Endpoint работает в режиме `sync_response`. После успешной обработки 1C получает
HTTP 200 и JSON, где полезный результат продублирован в двух полях. `response`
и `body` должны содержать один и тот же объект:

```json
{
  "success": true,
  "accepted": true,
  "status": "completed",
  "event_id": "c87bc74f-41ef-4995-9fb7-7390dbb39481",
  "response": {
    "success": true,
    "status": "forwarded",
    "message": "Accepted 2010 marking codes as KM_260703-5442___2010_pcs.txt; status=forwarded",
    "export": {
      "order_number": "260703/5442",
      "file_name": "KM_260703-5442___2010_pcs.txt",
      "total_codes": 2010,
      "status": "forwarded"
    },
    "dnp_forward": {
      "ok": true,
      "order_1c_number": "260703/5442",
      "order_dnp_name": "26-0703/5442",
      "created_count": 2010
    }
  },
  "body": {
    "success": true,
    "status": "forwarded",
    "message": "Accepted 2010 marking codes as KM_260703-5442___2010_pcs.txt; status=forwarded",
    "export": {
      "order_number": "260703/5442",
      "file_name": "KM_260703-5442___2010_pcs.txt",
      "total_codes": 2010,
      "status": "forwarded"
    },
    "dnp_forward": {
      "ok": true,
      "order_1c_number": "260703/5442",
      "order_dnp_name": "26-0703/5442",
      "created_count": 2010
    }
  }
}
```

`response` - основной ответ OMH. `body` оставлен как совместимый alias для
интеграций, которые ожидают поле с таким именем. Для 1C достаточно проверять
HTTP 2xx и сохранять весь текст ответа в регистр статусов.

## Как собрать через UI

1. Откройте `Scenario Library`.
2. Найдите `1C CHZ code pool delivery`.
3. Нажмите `Preview`.
4. Нажмите `Install scenario`.
5. Откройте созданный flow в `Integration Flows`.
6. Откройте `Visual Flow Builder`.
7. В шаге `CHZ pool delivery` проверьте:
   - `Номер заказа из 1С`: `request.body.order_number`;
   - `Источник кодов`: `Base64 full codes из 1С`;
   - `Массив Base64-кодов`: `request.body.full_codes_base64`;
   - `Сохранить результат как`: `marking_pool_export`.
8. В `Return response` верните `{{marking_pool_export}}`.
9. Запустите Preview, затем Test Console.

## Где настраиваются действия

Папка outbox, SMB-папка лазера, DnP URL и timeout не задаются в каждом flow.
Они настраиваются один раз:

```text
Marking Code Pools -> Settings
```

или через Environment Variables:

```text
CHZ_LASER_FILE_ENABLED
CHZ_LASER_SMB_UNC
CHZ_LASER_SMB_USERNAME
DNP_CHZ_CODE_POOL_IMPORT_URL
DNP_REQUEST_TIMEOUT_SECONDS
```

## Что проверять в Timeline

- `marking_code_pool_export_request.json` - что пришло из 1C.
- `marking_code_pool_export_response.json` - итоговый статус.
- `marking_code_pool_export_actions.json` - отдельно outbox, laser file и DnP.
- `return_response.json` - что вернулось в 1C.

В HTTP-ответе `body` и `response` должны содержать одинаковый полезный результат.
Если `body` пустой, значит endpoint или flow работает не в актуальной версии.

## Частые ошибки

- Нет `full_codes_base64`: 1C отправила неполный payload.
- Передали `КодМаркировки` вместо `ПолныйКодМаркировки`: реальный криптохвост
  может потеряться.
- SMB-папка выключена или недоступна: OMH вернет `partial_success`, но DnP
  forward может пройти.
- DnP URL не настроен: файл сохранится, но external forward будет disabled.
