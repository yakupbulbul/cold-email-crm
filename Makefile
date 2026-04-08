SHELL := /bin/zsh

.DEFAULT_GOAL := help

ENV_FILE ?= .env
COMPOSE := docker compose --env-file $(ENV_FILE)
PYTHON_BIN := backend/.venv/bin/python
PIP_BIN := backend/.venv/bin/pip
NPM_BIN := npm

.PHONY: help setup up down logs migrate bootstrap-admin seed dev dev-full \
	test reset full-up full-down test-infra-up test-infra-down \
	test-backend test-frontend test-e2e smoke check-env check-docker host-check

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

dev: check-env host-check ## Run frontend and backend on the host (lean mode)
	./scripts/dev.sh $(ENV_FILE) lean

dev-full: check-env host-check ## Run frontend, backend, worker, and scheduler on the host
	./scripts/dev.sh $(ENV_FILE) full

test: test-backend test-frontend test-e2e ## Run the local validation suite

test-backend: check-env ## Run backend tests against the test infra
	@/bin/zsh -lc 'set -a; source $(ENV_FILE); source .env.test.local 2>/dev/null || true; set +a; cd backend && ../$(PYTHON_BIN) -m pytest tests/api tests/integration -v'

test-frontend: check-env ## Run frontend lint checks
	cd frontend && $(NPM_BIN) run test:frontend

test-e2e: check-env ## Run Playwright end-to-end tests
	cd frontend && $(NPM_BIN) run test:e2e

smoke: check-env ## Run local backend connectivity smoke checks
	@/bin/zsh -lc 'set -a; source $(ENV_FILE); set +a; curl -fsS "$${BACKEND_URL}/api/v1/health" && echo && curl -fsS "$${BACKEND_URL}/api/v1/health/db" && echo && curl -fsS "$${BACKEND_URL}/api/v1/health/redis" && echo'

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
