# Release Checklist

## Local Gate
- Run `make release-check-local` (includes `py_compile`, `pytest`, `npm run build`, `openapi-check`, `route-inventory-check`, `check-official-packages`).
- Confirm `frontend/src/api/generated/openapi.json` is strictly up to date (`make openapi-check`).
- Confirm `python scripts/route_inventory_check.py` reports no errors.

## Docker Gate
- Copy `.env.production.example` to `.env.production` and replace secrets.
- Run `make release-check-docker` on a clean fixture database.
- Confirm `make doctor` returns no `error` checks.
- Confirm `/api/health/ready` returns HTTP 200 (returns HTTP 503 if unready/unhealthy).
- Run `make ui-smoke-live` and `make ui-deep-smoke-live` against the live stack.

## Runtime Scenarios
- Run `python backend/scripts/seed_release_fixtures.py` before live release e2e.
- Run `E2E_BASE_URL=http://localhost:8000 make e2e-release`.
- Verify success path, business/REST error fidelity, printer dry-run, retry, DLQ edit-and-retry, route inventory and production doctor.

## Backup And Rollback
- Switch to update mode via CLI without exposing credentials: `make prod-update-mode-on`.
- Run `make prod-backup` (records format and SHA256 checksum in metadata).
- Keep the latest config export and database dump outside the deployment directory.
- Verify restore capability using `make prod-restore FILE=<dump_or_sql_path>`.
- For config regression, use `/api/production/import-config/preview` before `/api/production/import-config/apply`.
- Resume processing once verified: `make prod-update-mode-off`.

## Production Startup
- Run `make docker-prod-up` only with a populated `.env.production`.
- Run `python -m app.cli.production doctor` after migrations.
- Open Production page and resolve every action-required first-run checklist item.
