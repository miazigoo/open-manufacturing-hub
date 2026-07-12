# Pattern Readiness Checklist

Pattern readiness is the implementation quality gate for integration patterns. It is different from Integration Coverage Matrix: coverage says which business scenarios OMH supports; readiness says whether a wizard/workbench is safe to present to users.

## Certification statuses

- `not_started` - the pattern is known, but should not be started from Simple Mode.
- `partial` - the wizard/workbench exists, but training, troubleshooting, tests or UX contract still has gaps.
- `ready_for_training` - the scenario can be taught and tested in Training Sandbox.
- `ready_for_production` - production evidence exists: smoke run, troubleshooting, run history and disabled-by-default save behavior are verified.
- `deprecated` - keep visible only for migration and support.

## Required checks

| Area | Gate |
| --- | --- |
| UI | Scenario Router card, wizard route, preview before write, disabled-by-default save, run-test path |
| Docs | `docs_link`, recipe, troubleshooting link |
| Training | Training Sandbox example for every ready pattern |
| Tests | pytest/e2e/smoke names registered in coverage |
| Timeline | user can inspect Timeline or run history after a test |
| Simple Mode | no visible `builder_json`, `workflow`, operation-template or raw config labels |

## Commands

```bash
make pattern-docs-check
make pattern-smoke
make simple-mode-ux-check
```

A pattern may stay `partial` without blocking the build, but it must show explicit actions in `/integration-patterns/certification`.
