# Мастер интеграции: входящий контракт

Используйте `/master`, когда начинаете новую интеграцию и ещё не нужно настраивать OData, foreach или target endpoint.

Цель первого шага — зафиксировать, кто вызывает OMH и что именно придёт во входящем запросе.

## Порядок работы

1. Откройте `/master`.
2. Выберите карточку сценария, например `DnP запрашивает пул кодов Честного знака`.
3. Проверьте формат входящего запроса: JSON, XML или raw text.
4. Проверьте sample request или вставьте реальный пример.
5. Нажмите `Разобрать поля`.
6. Проверьте таблицу полей: путь, тип, пример и required/optional.
7. Выберите route key: для DnP это `sinc = dnp_sinc_pull_codes`, fallback `operation`.
8. Выберите business key: для DnP это `order_name`, fallback `Number`.
9. Проверьте endpoint slug и preview `POST /api/bus/in/<slug>`.
10. Нажмите `Сохранить draft`.

## Что получится

OMH сохранит `InputContract` draft:

```json
{
  "name": "DnP запрашивает пул кодов Честного знака",
  "slug": "dnp_sinc_pull_codes",
  "input_mode": "json",
  "source_system": "dnp",
  "fields": [
    {
      "name": "Number",
      "path": "request.body.Number",
      "type": "string",
      "required": true,
      "example": "260666/6938"
    }
  ],
  "operation_key": {
    "type": "field",
    "field_path": "request.body.sinc",
    "value": "dnp_sinc_pull_codes",
    "fallback_paths": ["request.body.operation"]
  },
  "business_key": {
    "path": "request.body.order_name",
    "fallback_paths": ["request.body.Number"]
  }
}
```

## Что не делаем на этом шаге

- Не настраиваем OData.
- Не создаём foreach.
- Не собираем JSON/XML response.
- Не отправляем данные во внешний endpoint.
- Не запускаем Timeline.

Эти действия появятся в следующих шагах мастера. Первый шаг должен быть понятным и проверяемым: входящий request → поля → route key → business key → draft contract.
