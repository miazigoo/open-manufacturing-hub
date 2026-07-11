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

## CHZ Code Pools To DnP

Endpoint `POST /api/marking-code-pools/onec/export-file` сохраняет пул кодов
маркировки из 1C в файл для лазера. Если задан DnP endpoint, OMH после записи
файла дополнительно отправляет этот же пул в DnP без чтения 1C OData.

Переменные окружения:

```bash
OMH_DNP_CHZ_CODE_POOL_IMPORT_URL=http://<dnp-host>/api/v2/integrations/omh/chz/code-pools/from-1c
OMH_DNP_SHARED_SECRET=<same-token-as-dnp>
OMH_DNP_REQUEST_TIMEOUT_SECONDS=180
```

1C должна передавать `full_codes_base64`: DnP сам декодирует полный код
маркировки, сохраняет настоящий GS-разделитель и не создает дубли.
Если `OMH_DNP_CHZ_CODE_POOL_IMPORT_URL` пустой, поведение прежнее: OMH только
пишет файл в папку лазера.


## Frontend

```bash
cd ../frontend
npm install
npm run dev
```

The UI runs on `http://localhost:5173` and uses `VITE_API_BASE_URL` for the backend URL.
