# UI Inventory And Mode Classification

This inventory defines how current OMH pages should appear in Simple, Advanced and Developer modes.

## Simple Mode

Visible by default:

| Page | Route | Purpose |
| --- | --- | --- |
| Start | `/` | Scenario chooser: "Что вы хотите интегрировать?" |
| Documentation | `/docs` | Learning and reference |
| Training | `/training` | Safe executable lessons |
| 1C Cockpit | `/onec-cockpit` | Main 1C integration cockpit |
| Request/Response Workbench | `/test-console` | External service calls OMH, OMH returns JSON/XML/raw |
| OData Connections | `/odata-connections` | Named 1C OData connections |
| OData Explorer | `/odata-explorer` | Test OData, build filters, continue integration |
| Integration Flows | `/integration-flows` | Created integrations list and operations |
| Event Journal | `/events` | What happened |
| Transaction Monitor | `/runtime/monitor` | Runtime transaction state |
| Incidents | `/incidents` | Open operational problems |
| Health | `/health` | System health |
| Packages | `/packages` | Installable platform capabilities |
| Production | `/production` | Production safety and deployment state |

## Advanced Mode

Adds configuration, package and production ownership:

| Page | Route | Purpose |
| --- | --- | --- |
| Printing | `/printing` | Printer package operations |
| Plugin Store | `/plugin-store` | Package discovery |
| Business Objects | `/business-objects` | Object model |
| Resolvers | `/resolvers` | Object resolution |
| Resolver Cache | `/resolvers/cache` | Resolver diagnostics |
| Transforms | `/transforms` | Transformation library |
| Business Rules | `/business-rules` | Rule sets |
| Mappings | `/mappings` | Mapping editor |
| Test Cases | `/test-cases` | Saved integration tests |
| XML Tools | `/xml-tools` | Reusable XML toolbox |
| Connectors | `/connectors` | External connections |
| Secrets | `/secrets` | Secure credentials |
| Users | `/users` | Optional auth package users |
| Auth Settings | `/auth-settings` | Optional auth package settings |
| Environments | `/environments` | Environment profiles |
| Change Sets | `/change-sets` | Promotion and rollback |
| Notifications | `/notifications` | Operational notifications |
| Retention | `/retention` | Data retention |
| Audit Log | `/audit` | Change history |
| Queue | `/runtime/queue` | Queue operations |
| DLQ | `/runtime/dlq` | Dead letter recovery |
| Operation Keys | `/operation-keys` | Low-level trigger keys |
| Scenario Library | `/scenario-library` | Presets and reusable scenarios |
| Integration Designer | `/integration-designer` | Advanced builder |
| 1C Scenarios | `/onec-scenarios` | Advanced 1C scenarios |
| 1C Workbench | `/onec-workbench` | Advanced 1C workbench |
| Polling | `/polling` | Polling jobs |
| Maintenance | `/maintenance` | Maintenance operations |

## Developer Mode

Adds raw internal implementation pages:

| Page | Route | Purpose |
| --- | --- | --- |
| Integration Bus | `/integration-bus` | Raw endpoint and bus internals |
| Workflows | `/workflows` | Raw workflow entities |
| Execution Steps | `/execution/steps` | Runtime step internals |
| i18n Debug | `/i18n-debug` | Localization diagnostics |

## Refactor Targets

Pages that should be reviewed before adding more features:

- `/integration-flows`: keep as management of created integrations, not the main builder.
- `/operation-keys`: should be created from scenario context where possible.
- `/xml-tools`: should support Workbench and docs, not compete with Workbench.
- `/workflows` and `/execution/steps`: developer-only.
- `/mappings`: advanced-only unless embedded as a guided mapping step.

## Navigation Rule

If a route does not fit a real scenario, it must not appear in Simple mode.
