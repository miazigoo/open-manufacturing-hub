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

Production-вариант для 1C - видимый Integration Flow:

```text
POST /api/bus/in/onec-chz-pool-delivery
```

Оператор может установить его через UI: `Scenario Library -> 1C CHZ code
pool delivery -> Preview -> Install scenario`. После установки endpoint,
curl-пример, пример кода 1C и Timeline доступны в карточке flow.

Низкоуровневый endpoint `POST /api/marking-code-pools/onec/export-file`
остается системным API. Его использует flow step `marking_code_pool_export`.
Оба варианта принимают пул кодов маркировки из 1C и выполняют независимые
действия:

- сохраняет локальный outbox-файл внутри OMH;
- если настроена SMB-папка лазера, доставляет файл туда;
- если настроен DnP endpoint, отправляет этот же пул в DnP без чтения 1C OData.

Сбой одного действия не отменяет остальные. Например, если компьютер лазера
выключен, OMH вернет `partial_success`, но все равно отправит пул в DnP.

Базовые переменные окружения:

```bash
OMH_MARKING_CODE_POOL_EXPORT_DIR=/data/marking-code-pool-outbox
OMH_DNP_CHZ_CODE_POOL_IMPORT_URL=http://<dnp-host>/api/v2/integrations/omh/chz/code-pools/from-1c
OMH_DNP_REQUEST_TIMEOUT_SECONDS=180
OMH_CHZ_DNP_PACKED_CODES_EXPORT_URL=http://<dnp-host>/api/v2/integrations/omh/chz/packed-codes-export-for-1c
OMH_CHZ_DNP_PACKED_CODES_TIMEOUT_SECONDS=180
OMH_HEALTH_CHECKS_RETENTION_DAYS=7
OMH_CHZ_LASER_SMB_UNC=\\172.16.8.133\DataMatrixCodes
OMH_CHZ_LASER_SMB_USERNAME=guest
OMH_CHZ_LASER_SMB_PASSWORD=
OMH_CHZ_LASER_SMB_REQUIRE_SIGNING=false
OMH_CHZ_LASER_SMB_REQUIRE_SECURE_NEGOTIATE=false
```

Эти же значения можно задавать через веб-интерфейс OMH:
`Settings -> Environments -> Variables` у текущего environment. Ключи без
префикса `OMH_`:

```text
DNP_CHZ_CODE_POOL_IMPORT_URL
DNP_REQUEST_TIMEOUT_SECONDS
CHZ_DNP_PACKED_CODES_EXPORT_URL
CHZ_DNP_PACKED_CODES_TIMEOUT_SECONDS
CHZ_LASER_FILE_ENABLED
CHZ_LASER_SMB_UNC
CHZ_LASER_SMB_USERNAME
CHZ_LASER_SMB_PASSWORD
CHZ_LASER_SMB_REQUIRE_SIGNING
CHZ_LASER_SMB_REQUIRE_SECURE_NEGOTIATE
```

1C должна передавать `full_codes_base64`: DnP сам декодирует полный код
маркировки, сохраняет настоящий GS-разделитель и не создает дубли.
Если `OMH_DNP_CHZ_CODE_POOL_IMPORT_URL` пустой, поведение прежнее: OMH только
пишет файл.


## Frontend

```bash
cd ../frontend
npm install
npm run dev
```

The UI runs on `http://localhost:5173` and uses `VITE_API_BASE_URL` for the backend URL.
