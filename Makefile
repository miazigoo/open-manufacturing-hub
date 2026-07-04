.PHONY: install-backend install-frontend test-backend build-frontend lint-backend lint-frontend dev-backend dev-frontend demo-seed seed-local smoke-test integration-smoke ui-smoke ui-smoke-live openapi-export snapshot backup backup-config backup-db export-config pre-update-check post-update-check rollback-info restore-db packages-list package-install-onec package-install-printer docker-up docker-down

install-backend:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[test]"

install-frontend:
	cd frontend && npm install

test-backend:
	cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -e ".[test]" >/tmp/omh_make_backend_pip.log && pytest -q

build-frontend:
	cd frontend && npm install >/tmp/omh_make_frontend_npm.log && npm run build

lint-backend:
	cd backend && python3 -m compileall app scripts

lint-frontend:
	cd frontend && npm run build

dev-backend:
	cd backend && . .venv/bin/activate && alembic upgrade head && uvicorn app.main:app --reload

dev-frontend:
	cd frontend && npm run dev

demo-seed:
	docker compose exec -T backend python scripts/seed_demo.py

smoke-test:
	cd backend && python3 scripts/smoke_test.py

integration-smoke:
	cd backend && python3 scripts/integration_smoke.py

ui-smoke:
	cd frontend && npm run smoke:ui

ui-smoke-live:
	cd frontend && npm run smoke:ui:live

openapi-export:
	cd backend && . .venv/bin/activate && python -c "import json; from pathlib import Path; from app.main import app; target = Path('../frontend/src/api/generated/openapi.json'); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True), encoding='utf-8')"

snapshot:
	cd backend && . .venv/bin/activate && python -m app.cli.production snapshot

backup: backup-config backup-db

backup-config:
	cd backend && . .venv/bin/activate && python -m app.cli.production export-config

export-config: backup-config

backup-db:
	mkdir -p backups && docker compose exec -T postgres pg_dump -U omh omh > backups/omh-db-$$(date +%Y%m%d-%H%M%S).sql

restore-db:
	test -n "$(FILE)" || (echo "Usage: make restore-db FILE=backups/omh-db-YYYYMMDD-HHMMSS.sql" && exit 1)
	docker compose stop backend frontend
	docker compose exec -T postgres psql -U omh -d omh < "$(FILE)"
	docker compose start backend frontend

pre-update-check:
	cd backend && . .venv/bin/activate && python -m app.cli.production pre-update-check

post-update-check:
	cd backend && . .venv/bin/activate && python -m app.cli.production post-update-check

rollback-info:
	@cat docs/production/update-rollback.md

seed-local:
	cd backend && python3 scripts/seed_demo.py

docker-up:
	docker compose up

docker-down:
	docker compose down

packages-list:
	curl -s http://localhost:8000/api/packages/available | python3 -m json.tool

package-install-onec:
	curl -s -X POST http://localhost:8000/api/packages/omh-package-onec/install -H 'Content-Type: application/json' -d '{"install_demo_data": true}' | python3 -m json.tool

package-install-printer:
	curl -s -X POST http://localhost:8000/api/packages/omh-package-printer/install -H 'Content-Type: application/json' -d '{"install_demo_data": false}' | python3 -m json.tool
