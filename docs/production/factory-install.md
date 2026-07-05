# Factory Production Install

This runbook describes the supported single-host factory profile for Open Manufacturing Hub. It uses Docker Compose with PostgreSQL, backend API, queue worker, frontend and nginx reverse proxy.

## Target Architecture

```text
factory users / browsers
        |
        v
nginx :80
  |-- /api/*  -> backend :8000
  |-- /*      -> frontend :5173

backend :8000  -> postgres :5432
worker         -> postgres :5432
backups/       -> mounted host directory
```

The integration runtime is not blocked by the optional UI auth package. Auth gates the site only. Queue processing is handled by `worker`, not by browser sessions.

## Files In The Profile

| File | Purpose |
| --- | --- |
| `docker-compose.production.yml` | Production services, healthchecks and persistent volumes. |
| `.env.production.example` | Required backend, database, worker and public URL variables. |
| `frontend/.env.production.example` | Frontend production defaults. Keep `VITE_API_BASE_URL=/api` behind nginx. |
| `deploy/nginx/omh.conf` | Reverse proxy config for API and frontend. |
| `backups/db` | PostgreSQL dumps. |
| `backups/config` | Configuration exports created by the app. |
| `backups/snapshots` | Runtime snapshots for release evidence and support. |

## First Install

1. Prepare Docker and Docker Compose on the host.
2. Clone the repository.
3. Create the production env file:

```bash
cp .env.production.example .env.production
```

4. Edit `.env.production` and replace every `change-me` value.
5. Set `PUBLIC_BASE_URL` and `CORS_ORIGINS` to the real factory URL.
6. Keep `VITE_API_BASE_URL=/api` unless you intentionally bypass nginx.
7. Start the profile:

```bash
make prod-up
```

8. Run the doctor:

```bash
make prod-doctor
```

9. Open the site through nginx, for example `http://factory-host/`.
10. Open `/production` and complete the first-run checklist.

## Mandatory Secrets

Production startup fails when `OMH_SECRET_KEY` is absent. Use a long random value and store it outside chat/history/password managers shared with operators who should not administer the host.

Example generation:

```bash
python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
```

Do not commit `.env.production`. Only `.env.production.example` is tracked.

## Health Endpoints

Use these endpoints for host checks and external monitoring:

```bash
curl -fsS http://localhost/api/health/live
curl -fsS http://localhost/api/health/ready
```

`/api/health/live` checks that the API process responds. `/api/health/ready` checks database connectivity, migration revision, package registry, secret key and optionally worker heartbeat when `OMH_REQUIRE_WORKER_HEARTBEAT=true`.

## Worker

The queue worker runs independently:

```bash
python -m app.workers.queue_worker
```

In Compose it is a separate `worker` service. During update mode it stays alive but does not take new eligible queue work. It writes a heartbeat as component `queue-worker`, visible in production diagnostics.

## Backups

Create a full backup set:

```bash
make prod-backup
```

The command creates:

| Path | Content |
| --- | --- |
| `backups/db/omh-db-YYYYMMDD-HHMMSS.sql` | Full PostgreSQL dump. |
| `backups/config/omh-config-YYYYMMDD-HHMMSS.json` | Masked configuration export. |
| `backups/snapshots/omh-snapshot-YYYYMMDD-HHMMSS.json` | Runtime evidence snapshot. |

Copy these files off the production host after creation.

## Logs

Use:

```bash
make prod-logs
```

For a specific service:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml logs -f backend
docker compose --env-file .env.production -f docker-compose.production.yml logs -f worker
docker compose --env-file .env.production -f docker-compose.production.yml logs -f nginx
```

Do not paste logs with secrets into issue trackers. Connector passwords, tokens and recovery keys must be redacted first.

## Production Release Check

Run before handing the instance to users:

```bash
make prod-release-check
```

This validates the Compose file, runs the app doctor and checks live/ready endpoints through nginx.
