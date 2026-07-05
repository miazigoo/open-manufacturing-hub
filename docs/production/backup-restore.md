# Production Backup and Restore

This guide is for local Docker Compose deployments of Open Manufacturing Hub.
For the supported factory production profile, use the detailed runbook in
`docs/production/factory-install.md` and `docs/production/factory-restore.md`.

## Before Any Update

1. Enable update mode from `/production` or `POST /api/production/update-mode/enable`.
2. Create a production backup set: `make prod-backup`.
3. For local development only, `make backup-config` and `make backup-db` are still available.
4. Download/copy the generated files from `backups/db`, `backups/config` and `backups/snapshots` to a safe location outside the host.
5. Run `make pre-update-check` and fix errors before changing code or images.

## Config Export

Config exports include user-created configuration such as packages, connectors, endpoints, routes, integration flows, workflows, mappings, operation templates, OData lookup templates, resolvers, business rules, test cases, notification rules, maintenance windows and printer configs.

Runtime events, artifacts and queue contents are not exported by default. Secrets are masked. After import, re-enter passwords/tokens in connector and endpoint settings.

Create export:

```bash
make backup-config
```

API:

```bash
curl -X POST http://localhost:8000/api/production/export-config \
  -H 'Content-Type: application/json' \
  -d '{"secrets_policy":"masked"}'
```

## Database Backup

Create a full PostgreSQL dump:

```bash
make backup-db
```

Equivalent command:

```bash
mkdir -p backups/db
docker compose exec -T postgres pg_dump -U omh omh > backups/db/omh-db-$(date +%Y%m%d-%H%M%S).sql
```

## Config Import Restore

Use `/production` import preview first. Use `create_only` when restoring into an empty or new instance. Use `upsert` when updating existing objects. The importer never deletes existing objects in MVP.

## Database Restore

Stop workers/backend before restoring. For Compose deployments:

```bash
docker compose stop backend frontend
docker compose exec -T postgres psql -U omh -d omh < backups/db/omh-db-YYYYMMDD-HHMMSS.sql
docker compose start backend frontend
```

Or:

```bash
make prod-restore FILE=backups/db/omh-db-YYYYMMDD-HHMMSS.sql
```

## Verify Restore

1. `curl http://localhost:8000/api/health`
2. `curl http://localhost:8000/api/production/snapshot`
3. Run `make post-update-check`.
4. Open `/production`, `/integration-bus`, `/runtime/queue`, `/plugin-store`.
5. Re-enter masked secrets if the restore used config import.
