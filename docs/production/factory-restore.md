# Factory Restore Runbook

Use this when a production update, host incident or operator mistake requires restoring a database dump.

## Inputs Required

| Input | Example |
| --- | --- |
| Database dump | `backups/db/omh-db-20260706-142500.sql` |
| Matching config export | `backups/config/omh-config-20260706-142500.json` |
| Snapshot evidence | `backups/snapshots/omh-snapshot-20260706-142500.json` |
| Known good code/image | Git commit or image tag used when the backup was created. |

## Restore Database

```bash
make prod-restore FILE=backups/db/omh-db-YYYYMMDD-HHMMSS.sql
```

The command stops `worker`, `backend`, `frontend` and `nginx`, restores the dump through PostgreSQL, starts services again and runs `prod-doctor`.

## Manual Restore Equivalent

```bash
docker compose --env-file .env.production -f docker-compose.production.yml stop worker backend frontend nginx
docker compose --env-file .env.production -f docker-compose.production.yml exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backups/db/omh-db-YYYYMMDD-HHMMSS.sql
docker compose --env-file .env.production -f docker-compose.production.yml up -d backend worker frontend nginx
make prod-doctor
```

## Restore Configuration Only

Use the `/production` import tool when you need to restore configuration without replacing the whole database.

1. Open `/production`.
2. Upload `backups/config/omh-config-YYYYMMDD-HHMMSS.json`.
3. Run preview first.
4. Use `create_only` for an empty instance.
5. Use `upsert` only when you intentionally update existing objects.
6. Re-enter masked secrets after import.

## Post-Restore Checks

```bash
make prod-release-check
curl -fsS http://localhost/api/production/snapshot
```

Then click through the key UI pages:

- `/production`
- `/connectors`
- `/integration-bus`
- `/runtime/queue`
- `/plugin-store`
- `/docs`

Only disable update mode after queue state and connector health look correct.
