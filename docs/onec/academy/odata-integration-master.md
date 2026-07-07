# Мастер OData-интеграции

Используйте `/odata-explorer`, когда внешний сервис вызывает OMH, а OMH должен сходить в 1C OData, собрать JSON/XML/raw ответ или отправить результат дальше.

## Когда использовать

- Нужно принять JSON/XML/raw request от DnP, WMS, сайта или терминала.
- Нужно выполнить один или несколько OData-запросов в 1C.
- Нужно прочитать табличную часть объекта 1C через resource вида `Document_...(guid'{{order.Ref_Key}}')/Продукция`.
- Нужно повторить OData-запрос для каждой строки массива и объединить результат.
- Нужно сохранить настройку как реальный Integration Flow с endpoint и Timeline.

## Чем отличается от быстрой проверки OData

`Быстро проверить OData` только выполняет один запрос и показывает response.

`Собрать интеграцию` создает полный flow:

```text
Входящий запрос -> OData steps -> foreach OData -> payload -> response/endpoint -> Timeline
```

## Основные шаги

1. Вставьте пример входящего запроса.
2. Выберите OData connection.
3. Добавьте OData query, object/tabular query или foreach OData.
4. Настройте итоговое действие: вернуть JSON/XML/raw, отправить endpoint или accepted response.
5. Нажмите `Проверить интеграцию`.
6. Нажмите `Сохранить интеграцию`.
7. Скопируйте endpoint вида `POST /api/bus/in/<slug>`.
8. После теста откройте Timeline по `event_id`.

## Pagination

`$top` не может быть больше 500. Если нужно больше строк, ставьте `$top = 500` и включайте `Загружать следующие страницы`. OMH будет использовать `$skip` до `max_pages` из OData connection.

## Payload templates

Если JSON template содержит значение ровно `"{{codes}}"`, OMH вставит массив как настоящий JSON array, а не строку.
