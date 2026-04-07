#!/bin/zsh
set -euo pipefail

ENV_FILE="${1:-.env}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy .env.example to ${ENV_FILE} and fill in local values."
  exit 1
fi

set -a
source "${ENV_FILE}"
set +a

: "${BACKEND_HOST:=127.0.0.1}"
: "${BACKEND_PORT:=8050}"
: "${FRONTEND_PORT:=3000}"

if [[ ! -x backend/.venv/bin/python ]]; then
  echo "Missing backend/.venv. Run 'make setup' first."
  exit 1
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "Missing frontend/node_modules. Run 'make setup' first."
  exit 1
fi

trap 'kill 0' EXIT INT TERM

(
  cd backend
  ../backend/.venv/bin/python -m uvicorn app.main:app --reload --host "${BACKEND_HOST}" --port "${BACKEND_PORT}"
) &

(
  cd backend
  ../backend/.venv/bin/python -m celery -A app.workers.celery_app worker --loglevel=info
) &

(
  cd backend
  ../backend/.venv/bin/python -m celery -A app.workers.celery_app beat --loglevel=info
) &

(
  cd frontend
  npm run dev -- --hostname 0.0.0.0 --port "${FRONTEND_PORT}"
) &

wait
