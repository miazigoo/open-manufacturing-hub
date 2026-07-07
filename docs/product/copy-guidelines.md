# Product Copy Guidelines

These rules keep OMH understandable for a normal 1C user and useful for an integrator.

## Main Rule

Use the user's task language first. Use implementation terms second.

Good:

- "Внешний сервис обращается к OMH и ждёт ответ"
- "Найти заказ в 1C OData"
- "Вернуть XML ответ"
- "Проверить сценарий и открыть timeline"

Bad:

- "Create workflow"
- "Configure matcher group"
- "Edit action_json"
- "Run execution step"

Implementation terms are allowed when they are explained in the same screen.

## Russian Terminology

Use these forms in Russian UI:

- "интеграция" instead of "workflow" for the main user concept
- "сценарий" for a reusable business case
- "поток" only when referring to an existing Integration Flow entity
- "шаг" for a single action inside a scenario
- "входящий запрос" instead of "trigger payload"
- "ответ" instead of "response config"
- "журнал событий" instead of "event log" in visible headings
- "монитор транзакций" for runtime monitoring
- "пакет изменений" for change set
- "секрет" for stored password/token
- "режим разработчика" for developer UI mode

Allowed technical words without translation:

- 1C
- OData
- JSON
- XML
- HTTP
- API
- URL
- XPath
- curl
- POST, GET, PUT, PATCH

## Page Header Pattern

Every product page should answer:

1. What is this page for?
2. When should I use it?
3. What will happen after I press the primary button?

Example:

```text
Приём и ответ на запрос
Используйте, когда внешний сервис обращается к OMH, а OMH должен сходить в OData/API/XML и сразу вернуть ответ.
```

## Button Rules

Primary buttons should be verbs in user language:

- "Создать интеграцию"
- "Проверить запрос"
- "Сохранить как шаг"
- "Вернуть результат"
- "Открыть timeline"
- "Опубликовать в продакшен"

Avoid naked technical labels:

- "Submit"
- "Run"
- "Create"
- "Save"
- "Execute"

## Advanced Details

When a page exposes internal JSON, show it as:

- "Технические детали"
- "Посмотреть JSON"
- "Builder JSON"
- "Raw response"

The user should not need raw JSON to complete the happy path.

## Empty States

Empty states must explain the next useful action.

Good:

```text
Интеграций пока нет.
Начните с кнопки "Создать интеграцию" и выберите, кто обращается к OMH и какой ответ нужно вернуть.
```

Bad:

```text
No rows.
```

## Error Copy

Errors should say:

- what failed
- why it likely failed
- what to check next
- where to open the timeline or event

Example:

```text
OData не вернула заказ.
Проверьте подключение, имя ресурса и фильтр Number eq '260666/6938'. Откройте timeline, чтобы увидеть полный ответ 1C.
```
