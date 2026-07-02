.PHONY: install-backend install-frontend test-backend build-frontend lint-backend lint-frontend dev-backend dev-frontend demo-seed seed-local smoke-test docker-up docker-down

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

seed-local:
	cd backend && python3 scripts/seed_demo.py

docker-up:
	docker compose up

docker-down:
	docker compose down
