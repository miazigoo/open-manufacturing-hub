.PHONY: docs-platform-learning-check install-backend install-frontend check-test-env test-backend build-frontend lint-backend lint-frontend dev-backend dev-frontend demo-seed seed-local smoke-test integration-smoke pattern-smoke ui-smoke ui-smoke-live ui-deep-smoke-live i18n-check i18n-missing docs-check docs-quality-check docs-ru-language-check docs-examples-check integration-coverage-check integration-docs-coverage-check pattern-docs-check simple-mode-ux-check docs-screenshots openapi-export openapi-check route-inventory-check check-official-packages release-fixtures e2e-release release-check release-check-local release-check-docker doctor snapshot backup backup-config backup-db export-config pre-update-check post-update-check rollback-info restore-db packages-list package-install-onec package-install-printer docker-up docker-down docker-prod-up docker-prod-down prod-up prod-down prod-logs prod-migrate prod-backup prod-restore prod-doctor prod-release-check prod-update-mode-on prod-update-mode-off

PROD_COMPOSE = docker compose --env-file .env.production -f docker-compose.production.yml
PROD_HTTP_URL ?= http://localhost:$${HTTP_PORT:-80}
# Interpreter used to create backend/.venv when it does not exist yet.
PYTHON ?= python3

install-backend:
	cd backend && { [ -x .venv/bin/python ] || $(PYTHON) -m venv .venv; } && . .venv/bin/activate && pip install -e ".[test]"

install-frontend:
	cd frontend && npm install

check-test-env: install-backend
	cd backend && . .venv/bin/activate && python scripts/check_test_env.py

test-backend: check-test-env
	cd backend && . .venv/bin/activate && pytest -q

build-frontend:
	cd frontend && npm install >/tmp/omh_make_frontend_npm.log && npm run build

lint-backend: check-test-env
	cd backend && . .venv/bin/activate && python -m compileall app scripts

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

pattern-smoke:
	cd backend && . .venv/bin/activate && python scripts/pattern_smoke.py

ui-smoke:
	cd frontend && npm run smoke:ui

ui-smoke-live:
	cd frontend && npm run smoke:ui:live

ui-deep-smoke-live:
	cd frontend && npm run smoke:ui:deep:live

i18n-check:
	cd frontend && npm run i18n:check

i18n-missing:
	cd frontend && npm run i18n:missing

docs-check:
	cd frontend && npm run check:docs

docs-quality-check:
	cd frontend && npm run docs:quality-check

docs-ru-language-check:
	cd frontend && npm run docs:ru-language-check

docs-platform-learning-check:
	cd frontend && npm run docs:platform-learning-check

docs-examples-check:
	cd backend && . .venv/bin/activate && python scripts/check_docs_examples.py

integration-coverage-check:
	cd backend && . .venv/bin/activate && python scripts/check_integration_coverage.py --write-report

integration-docs-coverage-check: integration-coverage-check

pattern-docs-check:
	cd backend && . .venv/bin/activate && python scripts/check_pattern_docs.py

simple-mode-ux-check:
	cd backend && . .venv/bin/activate && python scripts/check_simple_mode_ux.py

docs-screenshots:
	cd frontend && npm run docs:screenshots

openapi-export: check-test-env
	cd backend && . .venv/bin/activate && python scripts/openapi_check.py --write

openapi-check: check-test-env
	cd backend && . .venv/bin/activate && python scripts/openapi_check.py --check

route-inventory-check: check-test-env
	cd backend && . .venv/bin/activate && python scripts/route_inventory_check.py

check-official-packages: check-test-env
	cd backend && . .venv/bin/activate && python scripts/check_official_packages.py

release-fixtures:
	cd backend && . .venv/bin/activate && python scripts/seed_release_fixtures.py

e2e-release:
	cd backend && python3 scripts/e2e_scenarios.py

release-check: release-check-local

release-check-local: lint-backend test-backend build-frontend openapi-check route-inventory-check check-official-packages
	@echo "release-check-local OK"

release-check-docker:
	docker compose down --remove-orphans
	docker compose up -d --build
	docker compose exec -T backend alembic upgrade head
	docker compose exec -T backend python scripts/seed_release_fixtures.py
	SMOKE_BASE_URL=http://localhost:8000 $(MAKE) smoke-test
	SMOKE_BASE_URL=http://localhost:8000 $(MAKE) integration-smoke
	E2E_BASE_URL=http://localhost:8000 $(MAKE) e2e-release
	$(MAKE) ui-smoke-live
	$(MAKE) ui-deep-smoke-live
	docker compose exec -T backend python -m app.cli.production doctor
	@echo "release-check-docker OK"

doctor:
	cd backend && . .venv/bin/activate && python -m app.cli.production doctor

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

docker-prod-up:
	$(MAKE) prod-up

docker-prod-down:
	$(MAKE) prod-down

prod-up:
	test -f .env.production || (echo "Copy .env.production.example to .env.production and replace secrets first." && exit 1)
	mkdir -p backups/db backups/config backups/snapshots
	$(PROD_COMPOSE) up -d --build

prod-down:
	$(PROD_COMPOSE) down

prod-logs:
	$(PROD_COMPOSE) logs -f --tail=200

prod-migrate:
	$(PROD_COMPOSE) run --rm backend alembic upgrade head

prod-backup:
	test -f .env.production || (echo "Missing .env.production" && exit 1)
	mkdir -p backups/db backups/config backups/snapshots
	$(PROD_COMPOSE) exec -T postgres sh -c 'pg_dump -U "$$POSTGRES_USER" "$$POSTGRES_DB"' > backups/db/omh-db-$$(date +%Y%m%d-%H%M%S).sql
	$(PROD_COMPOSE) exec -T backend python -m app.cli.production export-config --json
	$(PROD_COMPOSE) exec -T backend python -m app.cli.production snapshot > backups/snapshots/omh-snapshot-$$(date +%Y%m%d-%H%M%S).json

.PHONY: prod-restore-drill
prod-restore: RECOVERY_OPTIONS = --keep-db
prod-restore prod-restore-drill:
	test -f "$(FILE)" || (echo "Supply FILE pointing to a PostgreSQL backup" && exit 1)
	$(PROD_COMPOSE) --profile restore up -d --wait restore-db
	$(PROD_COMPOSE) --profile restore run --rm --build -T -v "$(abspath $(dir $(FILE))):/input:ro" restore-client --file "/input/$(notdir $(FILE))" $(RECOVERY_OPTIONS)

prod-doctor:
	$(PROD_COMPOSE) exec -T backend python -m app.cli.production doctor

prod-release-check:
	$(PROD_COMPOSE) config >/dev/null
	$(MAKE) prod-doctor
	curl -fsS $(PROD_HTTP_URL)/api/health/live >/dev/null
	curl -fsS $(PROD_HTTP_URL)/api/health/ready >/dev/null
	@echo "prod-release-check OK"

prod-update-mode-on:
	$(PROD_COMPOSE) exec -T backend python -m app.cli.production update-mode enable

prod-update-mode-off:
	$(PROD_COMPOSE) exec -T backend python -m app.cli.production update-mode disable

packages-list:
	curl -s http://localhost:8000/api/packages/available | python3 -m json.tool

package-install-onec:
	curl -s -X POST http://localhost:8000/api/packages/omh-package-onec/install -H 'Content-Type: application/json' -d '{"install_demo_data": true}' | python3 -m json.tool

package-install-printer:
	curl -s -X POST http://localhost:8000/api/packages/omh-package-printer/install -H 'Content-Type: application/json' -d '{"install_demo_data": false}' | python3 -m json.tool
