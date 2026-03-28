.PHONY: up down logs migrate restart build frontend-build backend-build help
.DEFAULT_GOAL := help

up: ## Start all infrastructure components in detached mode
	docker compose up -d

down: ## Stop all infrastructure components
	docker compose down

restart: ## Refresh the composition containers
	docker compose down && docker compose up -d

logs: ## Tail the logs of the entire stack
	docker compose logs -f

logs-api: ## Tail API backend logs
	docker compose logs -f api

logs-worker: ## Tail Celery worker logs
	docker compose logs -f worker

migrate: ## Execute Alembic database migrations internally
	docker compose exec api /bin/bash -c "source venv/bin/activate && alembic upgrade head"

build: ## Rebuild all docker images natively
	docker compose build

frontend-build: ## Build NextJS prod deployment
	docker compose build frontend

backend-build: ## Build FastAPI app
	docker compose build api worker scheduler

shell: ## SSH directly into the running python container securely
	docker compose exec api /bin/bash

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ─── Staging ────────────────────────────────────────────────────────────────
staging-up: ## Boot full staging stack (includes Mailpit SMTP/IMAP stub)
	docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d --build
	@echo "✅  Staging up. Mailpit UI: http://localhost:8025"

staging-down: ## Tear down staging stack
	docker compose -f docker-compose.yml -f docker-compose.staging.yml down

# ─── Test infra ─────────────────────────────────────────────────────────────
test-infra-up: ## Start minimal postgres+redis test containers
	docker compose -f docker-compose.test.yml up -d
	@sleep 3

test-infra-down: ## Stop test containers
	docker compose -f docker-compose.test.yml down

# ─── Backend Tests ──────────────────────────────────────────────────────────
test-api: ## Run pytest API unit tests (fast, no external services)
	cd backend && source venv/bin/activate && \
	  pytest tests/api -v \
	  --junitxml=../artifacts/pytest/results.xml \
	  --cov=app --cov-report=xml:../artifacts/pytest/coverage.xml \
	  --cov-report=term-missing

test-integration: ## Run integration tests (requires staging services)
	cd backend && source venv/bin/activate && \
	  pytest tests/integration -v -m integration \
	  --junitxml=../artifacts/pytest/integration-results.xml

# ─── Frontend E2E ──────────────────────────────────────────────────────────
test-e2e: ## Run Playwright E2E tests headlessly
	cd frontend && npx playwright test --reporter=list

test-e2e-headed: ## Run Playwright E2E tests in headed mode
	cd frontend && npx playwright test --headed

test-e2e-smoke: ## Run only smoke E2E tests (dashboard + ops)
	cd frontend && npx playwright test tests/e2e/dashboard.spec.ts tests/e2e/ops.spec.ts

# ─── Release Validation ─────────────────────────────────────────────────────
test-release: test-api test-integration test-e2e ## Run full release validation
	@echo "✅  All release validation tests complete."

# ─── Data Management ────────────────────────────────────────────────────────
reset-test-data: ## Reset deterministic staging/test seed data
	cd backend && source venv/bin/activate && python scripts/seed_test_data.py --reset

seed-staging: ## Seed staging environment with demo data
	cd backend && source venv/bin/activate && python scripts/seed_test_data.py

# ─── Artifacts ──────────────────────────────────────────────────────────────
show-report: ## Open Playwright HTML report
	cd frontend && npx playwright show-report ../artifacts/playwright

setup-artifacts: ## Create artifact directories
	mkdir -p artifacts/playwright artifacts/pytest artifacts/release
