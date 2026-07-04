# Open Manufacturing Hub

Open Manufacturing Hub is an open source integration runtime for ERP, WMS, MES and industrial automation. It makes integrations observable, replayable and debuggable before real connectors are added.

## Core Concepts

- **Event**: one business event moving between systems.
- **Run**: one execution attempt, replay, edit replay or dry run.
- **Step**: a pipeline stage such as receive, validate or send.
- **Artifact**: immutable JSON evidence produced by a step.
- **Timeline**: the operational view of what happened and why.
- **Replay**: rerun an event fully or from a selected step.
- **Dry Run**: simulate without external side effects.
- **Incident**: grouped repeated failures by fingerprint.
- **Health**: site and component availability.
- **Notification**: delivery rules and logs.
- **Retention**: cleanup for expired data while preserving pinned events.
- **Connector**: a source/target plugin instance such as Mock ERP, Mock WMS, REST or Webhook.
- **Mapping**: immutable versioned JSON transformation between source, canonical and target shapes.
- **Workflow**: configurable event route that binds steps, validation rules and mapping versions.
- **Execution Engine**: generic runtime that executes registered steps and records artifacts, retries and failure handlers.
- **1C HTTP Service**: configurable bidirectional target contract for sending WMS facts/statuses back to 1C without COM or direct SQL.

## Quick Start

```bash
docker compose up
```

Open:

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

Seed demo data after the containers are running:

```bash
make demo-seed
```

If you run the backend locally instead of Docker, use:

```bash
make seed-local
```

## Integration Guide

Use [docs/integration-guide.md](docs/integration-guide.md) as the implementation contract for external systems. It includes direct event API, webhook ingress, REST targets, 1C integration, heartbeat, correlation rules and production readiness checks.

Ready-to-use request bodies are in [examples](examples):

- `event.sales-order-created.json`: direct `POST /api/events` envelope.
- `webhook.sales-order-created.json`: webhook ingress payload.
- `connector.webhook-source.json`: source webhook connector.
- `connector.rest-target.json`: target REST connector.
- `connector.zpl-printer.json`: Zebra-compatible RAW TCP ZPL printer connector.
- `printing.chz-job.json`: sample Chestny Znak ZPL print job body for `POST /api/printing/jobs`.
- `connector.onec-bidirectional.json`: 1C bidirectional connector shape.
- `onec.xml-inbound.json`: 1C XML inbound wrapper for `POST /api/onec/xml/inbound`.
- `onec.odata-lookup.json`: OData lookup/enrichment body for `POST /api/onec/lookup/test`.
- `bus.endpoint.json`: named Integration Bus endpoint body for `POST /api/integration-bus/endpoints`.
- `bus.request.json`: sample JSON body for `POST /api/bus/in/{slug}`.
- `odata.lookup-template.json`: reusable OData lookup template body for `POST /api/odata-lookups`.
- `health.agent-heartbeat.json`: site agent heartbeat.

## Local Development

Backend:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Test and Build

```bash
make test-backend
make build-frontend
make ui-smoke
```

## Smoke Test

With the backend running locally or through Docker:

```bash
make smoke-test
make integration-smoke
```

Expected output includes:

```text
OK events
OK health
OK incidents
OK notifications
OK connector types
OK connectors
OK execution steps
OK mappings
OK workflows
OK maintenance
OK retention
OK create event
OK timeline
```

`make integration-smoke` additionally creates a temporary webhook connector, sends webhook and direct event payloads, verifies timelines, records a health heartbeat and removes the temporary connector.

For full UI regression coverage without Docker, run:

```bash
make ui-smoke
```

`make ui-smoke` prepares a temporary SQLite database, starts the backend and Vite frontend on free localhost ports, then runs Playwright through the critical routes, language switcher, transform/rule/resolver actions, visual flow preview and mobile viewport checks. Install the browser once with `cd frontend && npx playwright install chromium` if Playwright reports a missing browser.

## Demo Checklist

After `make demo-seed`, the UI should show:

- `SalesOrderCreated #1001` success event.
- `SalesOrderCreated #1532` failed event.
- an edit & replay example with failed run and successful `edit_replay` run.
- grouped `WAREHOUSE_NOT_FOUND at call_connector` incident.
- `Main Warehouse` health with internet down, WMS warning, ERP ok and queue size 342.
- `Critical WMS errors` notification rule.
- `Mock WMS` maintenance window.
- connector instances: Mock ERP / Mock WMS / REST Demo Target / Webhook Demo Source.
- workflow and mapping pages with demo ERP to canonical and canonical to WMS versions.
- 1C scenarios page with forward `1C ERP -> OMH -> WMS` and reverse `WMS -> OMH -> 1C ERP` demos.
- execution steps page with registered runtime steps.
- retention preview with expired artifacts/events and pinned skipped.
