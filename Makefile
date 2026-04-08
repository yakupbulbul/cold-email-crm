SHELL := /bin/zsh

.DEFAULT_GOAL := help

ENV_FILE ?= .env
COMPOSE := docker compose --env-file $(ENV_FILE)
PYTHON_BIN := backend/.venv/bin/python
PIP_BIN := backend/.venv/bin/pip
NPM_BIN := npm
K6_BIN := k6

.PHONY: help setup up down logs migrate bootstrap-admin seed dev dev-lean dev-full \
	test reset full-up full-down test-infra-up test-infra-down \
	test-backend test-frontend test-e2e test-api test-load test-smoke test-full \
	test-e2e-auth test-e2e-ops test-e2e-empty test-e2e-boundary \
	test-load-smoke test-load-load test-load-stress test-load-soak \
	test-release smoke check-env check-docker host-check

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

check-env: ## Ensure the local .env file exists
	@test -f $(ENV_FILE) || (echo "Missing $(ENV_FILE). Copy .env.example to $(ENV_FILE) and fill in local values." && exit 1)

check-docker: ## Ensure the Docker daemon is available
	@docker info >/dev/null 2>&1 || (echo "Docker daemon is not running. Start Docker Desktop (or your Docker service) and retry." && exit 1)

host-check: check-env ## Verify host Postgres and Redis are reachable for no-Docker development
	@/bin/zsh -lc 'set -a; source $(ENV_FILE); set +a; $(PYTHON_BIN) -c "import os, redis; from urllib.parse import urlparse; from sqlalchemy import create_engine, text; pg_url=os.environ[\"POSTGRES_URL\"]; redis_url=os.environ[\"REDIS_URL\"]; engine=create_engine(pg_url); conn=engine.connect(); conn.execute(text(\"SELECT 1\")); conn.close(); pg=urlparse(pg_url); print(f\"Host PostgreSQL reachable at {pg.hostname or '\''127.0.0.1'\''}:{pg.port or 5432}\"); client=redis.Redis.from_url(redis_url, socket_timeout=2); client.ping(); rd=urlparse(redis_url); print(f\"Host Redis reachable at {rd.hostname or '\''127.0.0.1'\''}:{rd.port or 6379}\")"'

setup: check-env ## Install host development dependencies
	python3 -m venv backend/.venv
	$(PIP_BIN) install --upgrade pip
	$(PIP_BIN) install -r backend/requirements.txt
	cd frontend && $(NPM_BIN) install

up: check-env check-docker ## Start local Postgres and Redis for hybrid development
	$(COMPOSE) up -d --wait postgres redis

down: check-env check-docker ## Stop local containers
	$(COMPOSE) down --remove-orphans

logs: check-env check-docker ## Tail container logs for local infra
	$(COMPOSE) logs -f postgres redis

migrate: check-env ## Run Alembic migrations against the local database
	@/bin/zsh -lc 'set -a; source $(ENV_FILE); set +a; cd backend && ../$(PYTHON_BIN) -m alembic upgrade head'

bootstrap-admin: check-env ## Create only the local bootstrap admin user
	@/bin/zsh -lc 'set -a; source $(ENV_FILE); set +a; test "$${BOOTSTRAP_ADMIN_PASSWORD}" != "replace-with-a-local-admin-password" || (echo "Set BOOTSTRAP_ADMIN_PASSWORD in $(ENV_FILE) before running make bootstrap-admin." && exit 1); cd backend && ../$(PYTHON_BIN) scripts/create_user.py --email "$${BOOTSTRAP_ADMIN_EMAIL:-admin@example.com}" --password "$${BOOTSTRAP_ADMIN_PASSWORD}" --admin'

seed: check-env ## Insert deterministic safe demo data (no admin bootstrap)
	@/bin/zsh -lc 'set -a; source $(ENV_FILE); set +a; cd backend && ../$(PYTHON_BIN) scripts/seed_test_data.py --reset'

dev: check-env host-check ## Run frontend, backend, worker, and scheduler on the host
	./scripts/dev.sh $(ENV_FILE) full

dev-lean: check-env host-check ## Run frontend and backend on the host (low-RAM mode)
	./scripts/dev.sh $(ENV_FILE) lean

dev-full: check-env host-check ## Alias for the worker-enabled host runtime
	./scripts/dev.sh $(ENV_FILE) full

test: test-backend test-frontend test-e2e ## Run the local validation suite

test-api: test-backend ## Alias for backend/API milestone coverage

test-backend: check-env ## Run backend tests against the test infra
	@/bin/zsh -lc 'set -a; source $(ENV_FILE); source .env.test.local 2>/dev/null || true; set +a; cd backend && ../$(PYTHON_BIN) -m pytest tests/api tests/integration -v'

test-frontend: check-env ## Run frontend lint checks
	cd frontend && PATH=/opt/homebrew/bin:$$PATH $(NPM_BIN) run test:frontend

test-e2e: check-env ## Run Playwright end-to-end tests
	cd frontend && PATH=/opt/homebrew/bin:$$PATH $(NPM_BIN) run test:e2e

test-e2e-auth: check-env ## Run Playwright auth and route protection coverage
	cd frontend && PATH=/opt/homebrew/bin:$$PATH PLAYWRIGHT_BASE_URL=$${FRONTEND_URL:-http://localhost:3010} npx playwright test tests/e2e/auth.spec.ts --project=chromium --reporter=list

test-e2e-ops: check-env ## Run Playwright ops and settings coverage
	cd frontend && PATH=/opt/homebrew/bin:$$PATH PLAYWRIGHT_BASE_URL=$${FRONTEND_URL:-http://localhost:3010} npx playwright test tests/e2e/ops.spec.ts tests/e2e/settings.spec.ts --project=chromium --reporter=list

test-e2e-empty: check-env ## Run Playwright empty and error-state coverage
	cd frontend && PATH=/opt/homebrew/bin:$$PATH PLAYWRIGHT_BASE_URL=$${FRONTEND_URL:-http://localhost:3010} npx playwright test tests/e2e/empty_error_states.spec.ts --project=chromium --reporter=list

test-e2e-boundary: check-env ## Run Playwright boundary and secret-safety coverage
	cd frontend && PATH=/opt/homebrew/bin:$$PATH PLAYWRIGHT_BASE_URL=$${FRONTEND_URL:-http://localhost:3010} npx playwright test tests/e2e/boundary_security.spec.ts --project=chromium --reporter=list

test-smoke: smoke test-e2e-auth ## Run lightweight local smoke checks

test-load: test-load-smoke test-load-load ## Run the main k6 milestone suites

test-load-smoke: check-env ## Run k6 smoke checks
	@/bin/zsh -lc 'if ! command -v $(K6_BIN) >/dev/null 2>&1; then echo "Missing k6. Install it first, for example: brew install k6"; exit 1; fi; set -a; source $(ENV_FILE); set +a; K6_BASE_URL="$${BACKEND_URL}" K6_ADMIN_EMAIL="$${BOOTSTRAP_ADMIN_EMAIL:-admin@example.com}" K6_ADMIN_PASSWORD="$${BOOTSTRAP_ADMIN_PASSWORD}" $(K6_BIN) run performance/k6/smoke/api_smoke.js'

test-load-load: check-env ## Run k6 sustained load checks
	@/bin/zsh -lc 'if ! command -v $(K6_BIN) >/dev/null 2>&1; then echo "Missing k6. Install it first, for example: brew install k6"; exit 1; fi; set -a; source $(ENV_FILE); set +a; K6_BASE_URL="$${BACKEND_URL}" K6_ADMIN_EMAIL="$${BOOTSTRAP_ADMIN_EMAIL:-admin@example.com}" K6_ADMIN_PASSWORD="$${BOOTSTRAP_ADMIN_PASSWORD}" $(K6_BIN) run performance/k6/load/api_load.js'

test-load-stress: check-env ## Run k6 stress checks
	@/bin/zsh -lc 'if ! command -v $(K6_BIN) >/dev/null 2>&1; then echo "Missing k6. Install it first, for example: brew install k6"; exit 1; fi; set -a; source $(ENV_FILE); set +a; K6_BASE_URL="$${BACKEND_URL}" K6_ADMIN_EMAIL="$${BOOTSTRAP_ADMIN_EMAIL:-admin@example.com}" K6_ADMIN_PASSWORD="$${BOOTSTRAP_ADMIN_PASSWORD}" $(K6_BIN) run performance/k6/stress/api_stress.js'

test-load-soak: check-env ## Run k6 soak checks
	@/bin/zsh -lc 'if ! command -v $(K6_BIN) >/dev/null 2>&1; then echo "Missing k6. Install it first, for example: brew install k6"; exit 1; fi; set -a; source $(ENV_FILE); set +a; K6_BASE_URL="$${BACKEND_URL}" K6_ADMIN_EMAIL="$${BOOTSTRAP_ADMIN_EMAIL:-admin@example.com}" K6_ADMIN_PASSWORD="$${BOOTSTRAP_ADMIN_PASSWORD}" $(K6_BIN) run performance/k6/soak/api_soak.js'

test-full: test-backend test-frontend test-e2e test-load ## Run the full milestone test stack

test-release: check-env ## Run the release-readiness milestone workflow
	./scripts/test_release_readiness.sh

smoke: check-env ## Run local backend connectivity smoke checks
	@/bin/zsh -lc 'set -a; source $(ENV_FILE); set +a; curl -fsS "$${BACKEND_URL}/api/v1/health/" && echo && curl -fsS "$${BACKEND_URL}/api/v1/health/db" && echo && curl -fsS "$${BACKEND_URL}/api/v1/health/redis" && echo'

reset: check-env check-docker ## Recreate local Postgres and Redis volumes
	$(COMPOSE) down -v --remove-orphans
	$(COMPOSE) up -d --wait postgres redis

full-up: check-env check-docker ## Run the full application stack in Docker
	$(COMPOSE) --profile full up -d --build --wait

full-down: check-env check-docker ## Stop the full Docker stack
	$(COMPOSE) --profile full down --remove-orphans

test-infra-up: check-env check-docker ## Start isolated test Postgres and Redis
	docker compose --env-file $(ENV_FILE) -f docker-compose.test.yml up -d --wait

test-infra-down: check-env check-docker ## Stop isolated test Postgres and Redis
	docker compose --env-file $(ENV_FILE) -f docker-compose.test.yml down -v --remove-orphans
