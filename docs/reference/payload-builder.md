# Reference: Payload Builder

Payload Builder is `/master` Step 3A. It builds a body and saves it as a variable, usually `target_payload`.

It does not send HTTP requests, does not call a 1C HTTP service, does not return caller response, does not compile the full integration and does not touch queue, DLQ or runtime Timeline.

## API

```text
POST /api/integration-master/payload/preview
POST /api/integration-master/payload/validate
POST /api/integration-master/drafts/{draft_id}/payload-steps
```

## Input

```json
{
  "previous_variables": {
    "request": {"body": {"order_id": 10271, "order_name": "26-0666/6938", "Number": "260666/6938"}},
    "order": {"Ref_Key": "c3335ee4-43d0-11f1-8388-000c29b755c7", "Number": "260666/6938"},
    "products": [{"Номенклатура_Key": "ff22288c-2da4-11f1-8388-000c29b755c7"}],
    "codes": [{"КодМаркировки": "code-001", "GTIN": "04601234567890"}],
    "context": {"run_id": "run-001", "event_id": "evt-001"}
  },
  "payload_step": {
    "id": "build_dnp_payload",
    "type": "build_payload",
    "body_type": "json",
    "save_as": "target_payload",
    "json_mode": "raw_template",
    "template": {
      "payload": {
        "rows": "{{codes}}",
        "order_numbers_by_basis": {
          "{{order.Ref_Key}}": "{{order.Number}}"
        }
      }
    }
  }
}
```

## Placeholder Rules

- Exact JSON placeholder preserves arrays and objects: `"{{codes}}"` renders as a JSON array.
- Exact object placeholder preserves object type: `"{{order}}"` renders as a JSON object.
- Mixed template renders as string: `"dnp-chz-sync:{{request.body.order_name}}"`.
- Dynamic keys are rendered as strings: `{ "{{order.Ref_Key}}": "{{order.Number}}" }`.
- Dot/index paths are supported: `order.Ref_Key`, `codes.length`, `products[0].Номенклатура_Key`.
- Missing variable returns `VARIABLE_NOT_FOUND` with message `Переменная order.Ref_Key не найдена.`

## JSON Table Mode

Default DnP rows:

```text
omh.run_id <- context.run_id
omh.event_id <- context.event_id
omh.entity_id <- request.body.order_name
omh.event_type <- ChestniyZnakCodesSyncRequested
omh.entity_type <- DnPOrder
omh.source_system <- Open Manufacturing Hub
omh.target_system <- DnP
omh.correlation_id <- dnp-chz-sync:{{request.body.order_name}}
payload.rows <- codes
payload.order_id <- request.body.order_id
payload.odata_url <- http://172.16.3.19/erp_ptc/odata/standard.odata/InformationRegister_ПулКодовМаркировкиСУЗ
payload.order_name <- request.body.order_name
payload.onec_order_number <- order.Number
```

Dynamic object entry:

```text
object_path: payload.order_numbers_by_basis
key_source: order.Ref_Key
value_source: order.Number
```

## XML

```xml
<Response><RowsCount>{{codes.length}}</RowsCount></Response>
```

Values are XML-escaped and the rendered result must be well-formed XML.

## Raw Text

```text
OK order={{order.Number}} codes={{codes.length}}
```

## Save Result

```json
{
  "id": "build_dnp_payload",
  "type": "build_payload",
  "body_type": "json",
  "save_as": "target_payload",
  "last_preview_status": "success"
}
```
