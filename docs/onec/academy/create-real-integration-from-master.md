# Создаём реальную интеграцию из Master draft

Integration Master Step 5A превращает сохранённый draft в реальные объекты OMH:

```text
IntegrationEndpoint
IntegrationRoute
IntegrationFlow
Workflow builder_json
SavedTestCase
```

## Почему интеграция выключена по умолчанию

Новый endpoint создаётся с `enabled=false`, если вы специально не включили переключатель `Включить сразу`.

Причина простая: сначала нужно выполнить saved test case, открыть Timeline и проверить OData-запросы, payload и final action. Только после этого endpoint должен принимать реальные запросы от DnP, 1C, WMS или сайта.

## Порядок работы

1. Завершите Input Contract, OData steps, Payload Builder и Final Action.
2. Откройте `Шаг 5 — Создание интеграции`.
3. Нажмите `Проверить`.
4. Нажмите `Показать preview` и проверьте endpoint, route, flow, workflow и saved test case.
5. Оставьте `Включить сразу` выключенным.
6. Нажмите `Создать интеграцию`.
7. Запустите saved test case из success panel.
8. Откройте Timeline, если тест создал event.
9. Если всё корректно, нажмите `Включить интеграцию`.

## Что проверяет validate-for-compile

```text
POST /api/integration-master/drafts/{draft_id}/validate-for-compile
```

Проверяются:

- Input Contract: name, slug, input mode, sample, operation key, business key.
- OData steps: connection, resource, `$top`, `save_as`, зависимости между `order`, `products`, `codes`.
- Payload step: body type, template/table config, `save_as`, неизвестные placeholder roots.
- Final Action: URL, body source, return mode.
- Generated `builder_json`: совместимость с существующим Integration Flow runtime.

## Preview без записи в БД

```text
POST /api/integration-master/drafts/{draft_id}/compile-preview
```

Preview показывает, что будет создано, но ничего не сохраняет:

```text
Endpoint: POST /api/bus/in/{slug}
Route: matcher from operation key
Integration Flow: compiled builder_json
Workflow: compiled runtime steps
Saved Test Case: sample input from Input Contract
```

Raw `builder_json` скрыт в `Advanced details`.

## Создание интеграции

```text
POST /api/integration-master/drafts/{draft_id}/compile
```

Default request:

```json
{
  "enabled": false,
  "create_saved_test_case": true,
  "comment": "Initial integration created from master"
}
```

Если slug уже занят, OMH не перезаписывает существующий endpoint. Backend вернёт ошибку:

```text
Endpoint /api/bus/in/{slug} уже существует. Выберите другой slug.
```

## После создания

Success panel показывает:

- endpoint URL;
- curl example;
- ссылку на saved test case;
- кнопку dry-run test;
- ссылку на Integration Flow;
- кнопку enable.

Скопируйте endpoint и передайте его вызывающей системе только после успешного теста.

## Где найти созданный flow

Откройте `Integration Flows` или используйте ссылку из success panel. Flow содержит `builder_json`, compiled workflow, endpoint, route и sample payload для Test Console.
