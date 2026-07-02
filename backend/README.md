# Open Manufacturing Hub Backend

Core backend skeleton for observable, replayable integration events.

## Run

```bash
docker-compose up
```

API starts on `http://localhost:8000`.

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
