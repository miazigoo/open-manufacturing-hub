# Integration Requirements Matrix

Integration Requirements Matrix фиксирует реальные интеграционные сценарии OMH и их readiness: pattern, wizard/workbench, docs, training, troubleshooting, tests и known gaps.

Source of truth:

- Backend registry: `backend/app/integration_coverage/registry.py`
- API: `GET /api/integration-coverage`
- UI: `/integration-coverage`
- Scenario Router: `/integration-start`
- Generated report: `docs/reports/integration-coverage-report.md`

## Gate

Run before release or after changing integration patterns/docs:

```bash
make integration-coverage-check
make integration-docs-coverage-check
```

The gate fails when:

- registry has fewer than 11 requirements;
- duplicate `requirement_id` exists;
- `ready` scenario lacks wizard/workbench, docs, training, troubleshooting or E2E link;
- a `planned` scenario exposes a startable wizard route;
- docs/troubleshooting links marked ready/partial are not registered in frontend docs;
- ready E2E test names are not present in backend tests.

## Status Semantics

| Status | Meaning | Start from `/integration-start` |
| --- | --- | --- |
| `ready` | Scenario has full coverage | Yes |
| `partial` | Wizard/workbench exists, but explicit gaps remain | Yes, with visible gaps |
| `planned` | Scenario is known but not implemented enough to start | No |
| `missing_docs` | Wizard may exist, but docs coverage is insufficient | No |
| `missing_wizard` | Docs may exist, but wizard/workbench is missing | No |

## Current Matrix

Do not duplicate the full table in this markdown. Use the API/UI/report so product, docs and release gate stay aligned.
