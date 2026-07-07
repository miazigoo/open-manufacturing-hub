# Reference: OData Master API

Backend endpoints:

```text
GET  /api/odata-master/examples
POST /api/odata-master/preview
POST /api/odata-master/save
POST /api/odata-master/run-test
```

All endpoints are part of `omh-package-onec` and require the package to be installed and enabled.

## Wizard spec

Core fields:

```json
{
  "name": "DnP CHZ codes sync",
  "slug": "dnp_sinc_pull_codes",
  "source": {
    "system": "dnp",
    "input_mode": "json",
    "sample": {},
    "operation_key": { "field": "sinc", "value": "dnp_sinc_pull_codes" },
    "auth_mode": "none"
  },
  "steps": [],
  "final_action": {}
}
```

Supported OData step types:

- `odata_query`
- `odata_object_query`
- `foreach_odata`

Supported final actions:

- `return_response`
- `send_endpoint`
- `send_onec_http_service`
- `async_accepted`

Compiler output is an existing `IntegrationFlow` with `builder_json`, compiled workflow, endpoint, route and saved test case.

## Run test diagnostics

`POST /api/odata-master/run-test` returns:

```json
{
  "mode": "saved_flow",
  "result": {},
  "diagnostics": {
    "status": "completed",
    "event_id": "00000000-0000-0000-0000-000000000000",
    "timeline_url": "/events/00000000-0000-0000-0000-000000000000",
    "artifact_checklist": [
      {
        "step_id": "step_1_order",
        "step_name": "Find order",
        "step_type": "odata_query",
        "artifacts": ["odata_query_request.json", "odata_query_response.json", "odata_query_result.json"],
        "notes": ["Check connection, resource, query and row count."]
      }
    ],
    "next_actions": ["Open Timeline and inspect artifacts."]
  }
}
```

Preview-mode run test has no `event_id` or `timeline_url`; it still returns `artifact_checklist` so the UI can explain what will appear after saving and running the flow.

## Limits

- OData `$top` must be `<= 500`.
- Pagination is controlled by step `paginate=true` and OData connection `max_pages`.
- Exact JSON placeholders preserve arrays/objects.
