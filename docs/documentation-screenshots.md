# Documentation screenshots

The in-app documentation portal uses lightweight placeholders until verified production screenshots are available. Keep screenshots close to the frontend bundle so the docs remain deployable without external storage.

## Storage

Use `frontend/src/docs/assets/<package>/`:

- `frontend/src/docs/assets/core/`
- `frontend/src/docs/assets/onec/`
- `frontend/src/docs/assets/printer/`
- `frontend/src/docs/assets/auth/`
- `frontend/src/docs/assets/secrets/`
- `frontend/src/docs/assets/packages/`

## Naming

Use lowercase kebab-case and include the screen purpose:

```text
onec-cockpit-overview.annotated.png
odata-explorer-resource-query.annotated.png
xml-tools-hash-diff.annotated.png
printer-job-retry.annotated.png
```

## Annotation rules

- Mask real hostnames, tokens, passwords, personal data and production IDs.
- Use one accent color for callouts per screenshot.
- Prefer 1440px wide screenshots for desktop and 390px wide screenshots for mobile-specific flows.
- Add a short caption in the docs page near the screenshot directive.
- Replace only the placeholder that matches the exact UI state; do not add decorative screenshots.

## PDF export

`GET /api/docs/export-pdf` currently returns `501 DOCS_PDF_EXPORT_NOT_IMPLEMENTED`. Keep the endpoint contract stable until the HTML documentation and screenshot set are finalized.
