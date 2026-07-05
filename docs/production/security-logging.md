# Production Security And Logging Notes

## Secrets

- Keep `.env.production` out of Git.
- Replace `OMH_SECRET_KEY`, `POSTGRES_PASSWORD` and connector credentials before first use.
- Use the secrets package for connector passwords and API tokens when available.
- Configuration exports mask secrets by default; imported connectors may require credential re-entry.

## Network

- Put nginx or an external TLS terminator in front of the UI.
- Keep `VITE_API_BASE_URL=/api` for same-origin browser calls.
- Set `CORS_ORIGINS` to the real public URL, not `*`.
- Expose PostgreSQL only to the Docker network unless there is a controlled DBA requirement.

## Logs

- Backend and worker logs are operational evidence, not a secret store.
- Redact tokens, passwords, recovery keys and full payloads before sharing logs.
- Keep incident timestamps together with `backups/snapshots` files so support can compare runtime state.

## Update Safety

- Enable update mode before changing images, code or schema.
- Create `prod-backup` before every update.
- Run `prod-release-check` before returning the system to operators.
