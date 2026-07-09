# Reference: Integration Master Input Contract

`/master` is the scenario-first Integration Master entry point.

This first step answers one question:

```text
Who calls OMH and what exactly will arrive in the incoming request?
```

It does not build OData steps, foreach loops, response builders or final target calls. Those are later wizard steps.

## Product Route

```text
/master
```

The page shows scenario cards, input type selection, a sample request editor, parsed fields, route key selection, business key selection, endpoint slug preview and the final Input Contract JSON.

## Backend Endpoints

```text
GET  /api/integration-master/scenarios
POST /api/integration-master/input/parse
POST /api/integration-master/input/validate
POST /api/integration-master/input/save-draft
GET  /api/integration-master/drafts/{draft_id}
POST /api/integration-master/odata-step/preview
POST /api/integration-master/odata-step/test
POST /api/integration-master/odata-step/validate
POST /api/integration-master/drafts/{draft_id}/odata-steps
POST /api/integration-master/odata-object-step/preview
POST /api/integration-master/odata-object-step/test
POST /api/integration-master/odata-object-step/validate
POST /api/integration-master/drafts/{draft_id}/odata-object-steps
POST /api/integration-master/foreach-odata-step/preview
POST /api/integration-master/foreach-odata-step/test
POST /api/integration-master/foreach-odata-step/validate
POST /api/integration-master/drafts/{draft_id}/foreach-odata-steps
POST /api/integration-master/payload/preview
POST /api/integration-master/payload/validate
POST /api/integration-master/drafts/{draft_id}/payload-steps
POST /api/integration-master/final-action/preview
POST /api/integration-master/final-action/test
POST /api/integration-master/final-action/validate
POST /api/integration-master/drafts/{draft_id}/final-action
```

## Parse Request

```json
{
  "input_mode": "json",
  "scenario_key": "dnp_chz_code_pool",
  "sample": {
    "operation": "dnp_sinc_pull_codes",
    "sinc": "dnp_sinc_pull_codes",
    "order_id": 10271,
    "order_name": "26-0666/6938",
    "Number": "260666/6938"
  }
}
```

## Parse Response

```json
{
  "input_mode": "json",
  "fields": [
    {
      "name": "Number",
      "path": "request.body.Number",
      "type": "string",
      "required": true,
      "example": "260666/6938"
    }
  ],
  "suggested_operation_keys": [],
  "suggested_business_keys": []
}
```

## Input Contract

```json
{
  "name": "Синхронизация пула кодов Честного знака",
  "slug": "dnp_sinc_pull_codes",
  "input_mode": "json",
  "source_system": "dnp",
  "scenario_key": "dnp_chz_code_pool",
  "sample": {
    "operation": "dnp_sinc_pull_codes",
    "sinc": "dnp_sinc_pull_codes",
    "order_id": 10271,
    "order_name": "26-0666/6938",
    "Number": "260666/6938"
  },
  "fields": [
    {
      "name": "Number",
      "path": "request.body.Number",
      "type": "string",
      "required": true,
      "example": "260666/6938",
      "description": "Номер заказа в формате 1С"
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
  },
  "endpoint_url": "/api/bus/in/dnp_sinc_pull_codes"
}
```

## Step 2A: Single OData Query

After the Input Contract draft is saved, `/master` shows one OData Query Builder.

Supported in this step:

- choose one OData connection;
- set one OData resource;
- build or enter one `$filter`;
- set `$select`, `$top`, `$orderby` and pagination flag;
- set `save_as`, for example `order`;
- mark the result `required`;
- preview rendered filter and URL;
- test the query against the selected OData connection;
- append the OData step to the existing Integration Master draft.

Example request:

```json
{
  "input_contract": {
    "name": "Синхронизация пула кодов Честного знака",
    "slug": "dnp_sinc_pull_codes",
    "input_mode": "json",
    "source_system": "dnp",
    "sample": {
      "Number": "260666/6938"
    },
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
      "type": "endpoint"
    },
    "business_key": {
      "path": "request.body.Number"
    }
  },
  "sample_input": {
    "Number": "260666/6938"
  },
  "odata_step": {
    "connection_id": "11111111-1111-1111-1111-111111111111",
    "resource": "Document_ЗаказНаПроизводство2_2",
    "filter_mode": "builder",
    "filter_rule": {
      "field": "Number",
      "operator": "eq",
      "value_type": "variable",
      "value": "request.body.Number"
    },
    "select": ["Ref_Key", "Number", "Date", "Posted"],
    "top": 1,
    "orderby": "Date desc",
    "paginate": false,
    "save_as": "order",
    "required": true
  }
}
```

The filter template is:

```text
Number eq '{{request.body.Number}}'
```

With the sample above it renders as:

```text
Number eq '260666/6938'
```

If 1C returns one row, later steps may use:

```text
order.Ref_Key
order.Number
order.Date
order.Posted
```

If the result is empty and `required=true`, test returns `ODATA_RESULT_EMPTY`. This is intentional: a missing production order should stop the scenario before JSON/XML builder or endpoint send.

The draft stores OData steps in `odata_steps_json` and returns them as `draft.odata_steps`.

## Step 2B: 1C Object / Tabular Part Query

After one `odata_query` step is saved, `/master` can add one `odata_object_query` step.

This step reads a nested 1C object resource such as:

```text
Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция
```

Example request:

```json
{
  "input_contract": {},
  "previous_variables": {
    "order": {
      "Ref_Key": "c3335ee4-43d0-11f1-8388-000c29b755c7",
      "Number": "260666/6938"
    }
  },
  "odata_object_step": {
    "connection_id": "11111111-1111-1111-1111-111111111111",
    "object_variable": "order",
    "key_field": "Ref_Key",
    "key_type": "guid",
    "base_resource": "Document_ЗаказНаПроизводство2_2",
    "nested_resource": "Продукция",
    "select": ["Номенклатура_Key", "Количество", "КоличествоУпаковок"],
    "top": 100,
    "paginate": false,
    "save_as": "products",
    "required": true
  }
}
```

Preview returns:

```text
Template: Document_ЗаказНаПроизводство2_2(guid'{{order.Ref_Key}}')/Продукция
Rendered: Document_ЗаказНаПроизводство2_2(guid'c3335ee4-43d0-11f1-8388-000c29b755c7')/Продукция
```

Successful test returns array rows and future variables:

```text
products[]
products[0].Номенклатура_Key
products[0].Количество
products[0].КоличествоУпаковок
```

If `required=true` and the tabular part is empty, test returns `ODATA_TABULAR_PART_EMPTY`.

The saved draft item has `type=odata_object_query` and is stored in the same `odata_steps_json` list. This is not full integration compile.

## Step 2C: Foreach OData Over Array

After one `odata_object_query` step is saved, `/master` can add one `foreach_odata` step.

This step takes an array such as:

```text
products[]
```

For each row it exposes one local variable:

```text
product
```

Example request:

```json
{
  "input_contract": {},
  "previous_variables": {
    "order": {
      "Ref_Key": "c3335ee4-43d0-11f1-8388-000c29b755c7",
      "Number": "260666/6938"
    },
    "products": [
      {
        "Номенклатура_Key": "ff22288c-2da4-11f1-8388-000c29b755c7",
        "Количество": 180,
        "КоличествоУпаковок": 180
      }
    ]
  },
  "foreach_step": {
    "connection_id": "11111111-1111-1111-1111-111111111111",
    "items": "products",
    "item_as": "product",
    "resource": "InformationRegister_ПулКодовМаркировкиСУЗ",
    "filter": "Номенклатура_Key eq guid'{{product.Номенклатура_Key}}' and ДокументОснование eq cast(guid'{{order.Ref_Key}}', 'Document_ЗаказНаПроизводство2_2')",
    "select": ["ПолныйКодМаркировки", "ДокументОснование", "Номенклатура_Key", "Статус"],
    "top": 500,
    "paginate": true,
    "merge": "flatten",
    "save_as": "codes",
    "required": true,
    "limits": {
      "max_items": 100,
      "max_requests": 100,
      "max_result_rows": 10000
    },
    "test_limit": 1
  }
}
```

Preview renders the filter using the first row of `products[]`:

```text
Номенклатура_Key eq guid'ff22288c-2da4-11f1-8388-000c29b755c7' and ДокументОснование eq cast(guid'c3335ee4-43d0-11f1-8388-000c29b755c7', 'Document_ЗаказНаПроизводство2_2')
```

Successful test returns:

```text
source_count
items_processed
odata_requests
rows_found
result_preview
requests
```

The default merge mode is `flatten`, so rows from all nested OData responses become one array:

```text
codes[]
codes[0].ПолныйКодМаркировки
codes[0].Номенклатура_Key
```

Supported merge modes:

- `flatten` — one common result array;
- `group_by_item` — keep rows grouped by source item;
- `first_per_item` — take the first returned row per source item.

Safety limits are part of the saved step. They prevent accidental mass reads from 1C:

```text
max_items
max_requests
max_result_rows
```

If the source array is not an array, validation explains that an object should use a normal OData query or tabular part step. If `$top > 500`, validation asks to set `$top=500` and enable pagination.

The saved draft item has `type=foreach_odata` and is stored in the same `odata_steps_json` list. This is still not full integration compile.

## Step 3A: Payload Builder

After one `foreach_odata` step is saved, `/master` can add one `build_payload` step.

This step builds a body and saves it as a variable:

```text
save_as: target_payload
body_type: json | xml | raw_text
```

Available variables:

```text
request.body.order_id
request.body.order_name
request.body.Number
order.Ref_Key
order.Number
order.Date
products[]
products[0].Номенклатура_Key
codes[]
codes.length
codes[0].ПолныйКодМаркировки
context.run_id
context.event_id
```

JSON supports two modes:

- table fields;
- raw JSON template.

Exact JSON placeholder preserves arrays and objects:

```json
{
  "rows": "{{codes}}",
  "order": "{{order}}"
}
```

Mixed template becomes a string:

```json
{
  "correlation_id": "dnp-chz-sync:{{request.body.order_name}}"
}
```

Dynamic JSON keys are supported:

```json
{
  "payload": {
    "order_numbers_by_basis": {
      "{{order.Ref_Key}}": "{{order.Number}}"
    }
  }
}
```

XML template example:

```xml
<Response><RowsCount>{{codes.length}}</RowsCount></Response>
```

Raw text example:

```text
OK order={{order.Number}} codes={{codes.length}}
```

Missing path returns `VARIABLE_NOT_FOUND` and a friendly message such as `Переменная order.Ref_Key не найдена.`

The saved draft item has `type=build_payload` and is stored in the same `odata_steps_json` list. This step does not send the body anywhere.

## Step 4A: Final Action Builder

After one `build_payload` step is saved, `/master` can configure one `final_action` object on the draft.

Supported action types:

- `return_response` — return JSON/XML/raw body to the caller;
- `send_endpoint` — send `target_payload` to an external endpoint and return a configured caller response;
- `send_and_return_response` — send endpoint and proxy the endpoint response to the caller;
- `accepted_event` — return `event_id` and `queue_item_id` for async handling.

Example endpoint send:

```json
{
  "type": "send_endpoint",
  "method": "POST",
  "url": "http://172.16.3.10/api/v2/integrations/omh/chz/codes/import",
  "headers": {
    "Content-Type": "application/json"
  },
  "body_type": "json",
  "body_source": "target_payload",
  "timeout_seconds": 30,
  "return_to_caller": {
    "type": "fixed_success",
    "body": {
      "ok": true
    },
    "status_code": 200,
    "headers": {}
  }
}
```

`Preview final action` is dry: it renders the target request and caller response without network calls.

`Test final action` defaults to `dry_run=true`. A real test uses the configured endpoint and should be confirmed by the UI before sending.

Validation rules:

- URL is required for endpoint actions and must start with `http://` or `https://`;
- private and localhost URLs are allowed but produce warnings;
- `target_payload` must exist when `body_source=target_payload`;
- form body is reserved for a later step;
- timeout must be 1..300 seconds;
- caller status must be 100..599.

The saved final action is stored in `integration_master_drafts.final_action_json`. It is not appended to `odata_steps_json`.

## Parsing Rules

- JSON fields use paths like `request.body.operation`.
- JSON arrays include the array path, for example `request.body.items[]`, and first item paths such as `request.body.items[0].sku`.
- XML fields use internal paths like `xml./Документ/Номер` and display paths like `/Документ/Номер`.
- Raw text always exposes `request.raw_text`; simple `key=value` chunks are additionally exposed as `request.raw_text.key`.
- Sample size is limited to 256 KB.

## Slug Rule

Endpoint slug must contain only lowercase letters, numbers, `-` and `_`, and must start and end with a letter or number.

Valid:

```text
dnp_sinc_pull_codes
lookup-contractor
```

Invalid:

```text
DnP Codes
lookup contractor!
```

## Non-goals For Current Master Steps

Do not add here:

- saving full integration.
- Timeline and full dry-run execution.
- production queue execution, retry or DLQ.
- generated production endpoint publish.

## Step 5A: Compile Draft Into Real Integration

After `final_action` is saved, `/master` shows `Шаг 5 — Создание интеграции`.

New endpoints:

```text
POST /api/integration-master/drafts/{draft_id}/validate-for-compile
POST /api/integration-master/drafts/{draft_id}/compile-preview
POST /api/integration-master/drafts/{draft_id}/compile
POST /api/integration-master/compiled/{integration_flow_id}/run-test
POST /api/integration-master/compiled/{integration_flow_id}/enable
```

`validate-for-compile` checks Input Contract, OData dependencies, Payload Builder, Final Action and generated `builder_json`.

`compile-preview` does not write to the database. It returns `will_create` and `advanced.builder_json`.

`compile` creates real OMH objects transactionally:

```text
IntegrationEndpoint
IntegrationRoute
IntegrationFlow
Workflow
SavedTestCase
Audit events
```

The created integration is disabled by default:

```json
{
  "enabled": false,
  "create_saved_test_case": true
}
```

Duplicate slug is blocked. The compiler does not silently overwrite existing endpoints:

```text
Endpoint /api/bus/in/{slug} уже существует. Выберите другой slug.
```

After creation, run the saved test case, inspect Timeline artifacts, then call:

```text
POST /api/integration-master/compiled/{integration_flow_id}/enable
```

This enables the flow, endpoint, route and workflow.
