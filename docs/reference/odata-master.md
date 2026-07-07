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

## Limits

- OData `$top` must be `<= 500`.
- Pagination is controlled by step `paginate=true` and OData connection `max_pages`.
- Exact JSON placeholders preserve arrays/objects.
