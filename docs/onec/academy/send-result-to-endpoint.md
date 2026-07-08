# Отправить target_payload во внешний endpoint

Используйте Step 4A `Отправить на внешний endpoint`, когда после OData и payload builder нужно вызвать внешний API.

## Минимальная настройка DnP

```text
Action type: send_endpoint
Method: POST
URL: http://172.16.3.10/api/v2/integrations/omh/chz/codes/import
Headers: {"Content-Type":"application/json"}
Body source: target_payload
Body type: JSON
Timeout: 30
Return to caller: Fixed success {"ok": true}
```

## Headers и secrets

Headers задаются JSON object. Можно указать обычные строки:

```json
{
  "Content-Type": "application/json"
}
```

Можно заранее описать secret ref, но Step 4A не реализует secrets store:

```json
{
  "Authorization": {"$secret": "dnp_api_token"}
}
```

## Body source

- `target_payload` отправляет результат Step 3A.
- `custom` позволяет собрать body через placeholders.
- `none` отправляет запрос без body, полезно для `GET`/`DELETE`.

Form body отключен и появится позже. Сейчас поддержаны JSON, XML и raw text.

## Private URL warning

URL вида `localhost`, `127.0.0.1`, `10.*`, `172.16-31.*`, `192.168.*` разрешены, но preview покажет warning. Для production проверьте доступность адреса из backend-контейнера, а не из браузера оператора.

## Real test

Сначала нажмите `Dry run`. Если preview корректный, используйте `Real test endpoint`. Ответ target endpoint будет показан в панели test. Если target вернет `4xx/5xx`, OMH сохранит оригинальное тело ответа в результате test.
