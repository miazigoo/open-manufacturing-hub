# Factory Update Runbook

Use this flow for every production update. The goal is to stop risky processing, capture a restore point, update, verify, then resume.

## Safe Update Steps

1. Enable update mode:

```bash
make prod-update-mode-on
```

2. Create backup evidence:

```bash
make prod-backup
```

3. Run diagnostics:

```bash
make prod-doctor
```

4. Pull the new code or deploy the new image set.
5. Start/rebuild containers:

```bash
make prod-up
```

6. Run migrations if you started services manually:

```bash
make prod-migrate
```

7. Run release verification:

```bash
make prod-release-check
```

8. Open `/production`, confirm the checklist and doctor state.
9. Disable update mode only after verification passes:

```bash
make prod-update-mode-off
```

## What Update Mode Does

Update mode prevents workers from taking new eligible queue jobs. Incoming requests can still be accepted and queued depending on route configuration. It is not a maintenance page and it does not replace backups.

## If Verification Fails

Keep update mode enabled and collect:

```bash
make prod-doctor
make prod-logs
curl -fsS http://localhost/api/health/ready
```

If the database was migrated and rollback is required, restore from the pre-update DB dump using `factory-restore.md`.

## Operator Rules

- Do not update without a fresh `backups/db` dump.
- Do not disable update mode while `/api/health/ready` is `error`.
- Do not edit `.env.production` and restart blindly; run `make prod-doctor` after every env change.
- Do not use demo seed in production.
