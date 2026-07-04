.PHONY: install-backend install-frontend test-backend build-frontend lint-backend lint-frontend dev-backend dev-frontend demo-seed seed-local smoke-test integration-smoke ui-smoke openapi-export packages-list package-install-onec package-install-printer docker-up docker-down

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

openapi-export:
	cd backend && . .venv/bin/activate && python -c "import json; from pathlib import Path; from app.main import app; target = Path('../frontend/src/api/generated/openapi.json'); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True), encoding='utf-8')"

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
