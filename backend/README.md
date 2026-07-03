# Open Manufacturing Hub Backend

Core backend skeleton for observable, replayable integration events.

## Run

```bash
docker-compose up
```

API starts on `http://localhost:8000`.

## Integration Check

The external integration contract is documented in `../docs/integration-guide.md`.

With the backend running:

```bash
python3 scripts/integration_smoke.py
```

The check creates a temporary webhook source connector, sends webhook and direct events, verifies timelines and records a health heartbeat.

## Local Tests

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
pytest
```


## Frontend

```bash
cd ../frontend
npm install
npm run dev
```

The UI runs on `http://localhost:5173` and uses `VITE_API_BASE_URL` for the backend URL.
