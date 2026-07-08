# Вернуть JSON, XML или raw response вызывающей системе

Используйте Step 4A `Вернуть ответ вызывающей системе`, когда внешний caller ожидает синхронный ответ от OMH без отправки target endpoint.

## JSON response из target_payload

```text
Action type: return_response
Body source: target_payload
Response type: JSON
HTTP status: 200
Headers: {"Content-Type":"application/json"}
```

Caller получит body, собранный на Step 3A.

## Custom XML response

```text
Action type: return_response
Body source: custom
Response type: XML
HTTP status: 200
Headers: {"Content-Type":"application/xml"}
```

Template:

```xml
<Response>
  <Order>{{request.body.order_name}}</Order>
  <Codes>{{codes.length}}</Codes>
</Response>
```

Preview покажет rendered XML и ошибки отсутствующих переменных.

## Raw response

Raw text подходит для простых legacy callers:

```text
OK order={{request.body.order_name}} codes={{codes.length}}
```

## Proxy и accepted

Если нужно сначала отправить endpoint и вернуть его ответ caller'у, используйте `send_and_return_response`.

Если caller не должен ждать выполнения, используйте `accepted_event`: OMH вернет `event_id` и `queue_item_id`.
