# Production Update and Rollback Runbook

## Safe Update Flow

1. Open `/production`.
2. Enable update mode. New inbound requests remain queued and workers stop taking new jobs.
3. Create a config export.
4. Create a database backup.
5. Run pre-update check and resolve errors.
6. Pull/update code or images.
7. Run migrations.
8. Start backend/frontend.
9. Run post-update check.
10. Disable update mode only after checks pass.

## Commands

```bash
make pre-update-check
make backup-config
make backup-db
git pull
docker compose up -d --build
make post-update-check
```

## Rollback If Post-Update Fails

1. Keep update mode enabled if the app still responds.
2. Stop app containers:

```bash
docker compose stop backend frontend
```

3. Restore previous code/image:

```bash
git checkout <previous-known-good-commit>
docker compose up -d --build --no-start backend frontend
```

4. Restore the DB backup:

```bash
docker compose exec -T postgres psql -U omh -d omh < backups/omh-db-YYYYMMDD-HHMMSS.sql
```

5. Start app:

```bash
docker compose start backend frontend
```

6. Verify:

```bash
make post-update-check
curl http://localhost:8000/api/production/snapshot
```

## Notes

Rollback is intentionally manual in MVP. Do not run blind rollback scripts in a factory environment without checking database backup age, target commit/image and migration direction.
