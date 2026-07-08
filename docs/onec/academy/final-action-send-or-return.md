# Step 4A: выбрать финальное действие

Step 4A появляется в `/master` после сохранения `build_payload`.

Он отвечает на один вопрос:

```text
Что сделать с target_payload?
```

## Варианты

| Type | Когда использовать |
| --- | --- |
| `return_response` | Нужно сразу вернуть JSON/XML/raw вызывающей системе. |
| `send_endpoint` | Нужно отправить `target_payload` во внешний endpoint и вернуть фиксированный/custom ответ. |
| `send_and_return_response` | Нужно отправить endpoint и проксировать его ответ caller'у. |
| `accepted_event` | Нужно быстро принять запрос, вернуть `event_id`/`queue_item_id` и обработать асинхронно. |

## Переменные

Step 4A использует переменные предыдущих шагов:

```text
target_payload
request.body
context.run_id
context.event_id
context.queue_item_id
```

Если `target_payload` отсутствует, сначала вернитесь к Step 3A и сохраните payload builder.

## Preview

`Preview final action` ничего не отправляет во внешние системы. Он показывает:

- какой HTTP request будет отправлен, если выбран endpoint;
- что OMH вернет вызывающей системе;
- warnings по private/localhost URL;
- ошибки URL/body/status до real test.

## Test

`Dry run` не вызывает network. Его безопасно нажимать при любой конфигурации.

`Real test endpoint` отправляет настоящий HTTP-запрос на выбранный URL и требует подтверждение в UI.

## Что пока не делает Step 4A

- не публикует production endpoint;
- не компилирует полный integration flow;
- не запускает production queue/retry/DLQ;
- не создает реальный Timeline runtime.

Step 4A сохраняет только `final_action` в draft.
