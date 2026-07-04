# Release Checklist

## Local Gate
- Run `make release-check-local`.
- Confirm `frontend/src/api/generated/openapi.json` is up to date.
- Confirm `python scripts/route_inventory_check.py` reports no errors.

## Docker Gate
- Copy `.env.production.example` to `.env.production` and replace secrets.
- Run `make release-check-docker` on a clean fixture database.
- Confirm `make doctor` returns no `error` checks.
- Run `make ui-smoke-live` and `make ui-deep-smoke-live` against the live stack.

## Runtime Scenarios
- Run `python backend/scripts/seed_release_fixtures.py` before live release e2e.
- Run `E2E_BASE_URL=http://localhost:8000 make e2e-release`.
- Verify success path, business/REST error fidelity, printer dry-run, retry, DLQ edit-and-retry, route inventory and production doctor.

## Backup And Rollback
- Run `make backup-config` before deployment.
- Run `make backup-db` for docker PostgreSQL deployments.
- Keep the latest config export and database dump outside the deployment directory.
- For config regression, use `/api/production/import-config/preview` before `/api/production/import-config/apply`.

## Production Startup
- Run `make docker-prod-up` only with a populated `.env.production`.
- Run `python -m app.cli.production doctor` after migrations.
- Open Production page and resolve every action-required first-run checklist item.
