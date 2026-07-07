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
  "name": "DnP запрашивает пул кодов Честного знака",
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
    "name": "DnP запрашивает пул кодов Честного знака",
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

## Non-goals For Step 1

Do not add here:

- more than one OData step.
- foreach OData.
- tabular part helper.
- final action.
- response builder.
- saving full integration.
- run test or Timeline.
