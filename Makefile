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
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
