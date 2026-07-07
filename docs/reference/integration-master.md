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

- OData step configuration.
- foreach OData.
- final action.
- response builder.
- saving full integration.
- run test or Timeline.
