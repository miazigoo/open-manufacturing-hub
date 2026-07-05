# Documentation Quality Checklist

Use this checklist before publishing in-app documentation for production packages.

## Page Contract

- Page explains what the user sends and where it is sent.
- Page explains what OMH does internally: endpoint, event, route/flow, lookup, transform, target action.
- Page shows the outgoing target request or operation.
- Page shows the response returned to the caller.
- Page lists timeline steps and artifacts that should exist after execution.
- Page preserves original external-system error semantics instead of hiding them behind generic text.
- Page explains retry, edit retry, replay and DLQ behavior when the scenario can fail asynchronously.
- Page links to related in-app pages or routes.
- Page includes screenshot placeholders for major UI steps.
- Page includes copyable code blocks for payloads, commands and 1C snippets.

## 1C Scenario Coverage

- 1C package overview.
- 1C connector setup.
- Secrets and static inbound token.
- 1C -> external API or website.
- 1C POST -> two OData lookups -> JSON -> endpoint.
- 1C XML -> OMH -> 1C raw forwarding.
- 1C XML + INN lookup.
- 1C -> printer.
- Website/API -> 1C.
- 1C OData polling -> target system.
- WMS/API -> OMH -> 1C.
- Errors, timeline and artifacts.
- Queue, retry and DLQ.

## Frontend Checks

- `/docs` opens without package gates or runtime errors.
- Required 1C routes open directly by URL.
- RU content is detailed enough for a real 1C developer.
- EN/ZH pages keep the same structure and clearly mark translation progress when not fully localized.
- Code blocks render copy controls.
- Screenshot placeholders render as visible UI blocks.
- Tables and lists are readable on desktop and mobile.
- Existing `docLinks` do not point to removed sections.

## Backend API Checks

- `/api/docs/index?lang=ru` includes all 1C sections and pages.
- `/api/docs/pages/<page_id>?lang=ru` returns 200 for every documented 1C page.
- EN/ZH page API responses use `translation_status=in_progress` until fully localized.
- Unknown page ids return 404.
- PDF export endpoint keeps an explicit not-implemented contract until implemented.

## Release Gate

- `npm run check:docs` passes.
- `npm run build` passes.
- Backend docs portal tests pass.
- UI smoke covers representative `/docs/onec/...` routes.
