#!/bin/zsh
set -euo pipefail

ENV_FILE="${1:-.env}"
MODE="${2:-lean}"

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
: "${NODE_OPTIONS:=--max-old-space-size=2048}"

BACKGROUND_WORKERS_ENABLED_VALUE=false
if [[ "${MODE}" == "full" ]]; then
  BACKGROUND_WORKERS_ENABLED_VALUE=true
fi

if [[ ! -x backend/.venv/bin/python ]]; then
  echo "Missing backend/.venv. Run 'make setup' first."
  exit 1
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "Missing frontend/node_modules. Run 'make setup' first."
  exit 1
fi

trap 'kill 0' EXIT INT TERM

echo "Starting host development mode: ${MODE}"
echo "Backend:  ../backend/.venv/bin/python -m uvicorn app.main:app --reload --reload-dir app --host ${BACKEND_HOST} --port ${BACKEND_PORT}"
echo "Frontend: cd frontend && NODE_OPTIONS='${NODE_OPTIONS}' npm run dev -- --hostname 0.0.0.0 --port ${FRONTEND_PORT}"
echo "Worker:   cd backend && ../backend/.venv/bin/python -m celery -A app.workers.celery_app worker --loglevel=info"
echo "Beat:     cd backend && ../backend/.venv/bin/python -m celery -A app.workers.celery_app beat --loglevel=info"

(
  cd backend
  BACKGROUND_WORKERS_ENABLED="${BACKGROUND_WORKERS_ENABLED_VALUE}" ../backend/.venv/bin/python -m uvicorn app.main:app --reload --reload-dir app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}"
) &

if [[ "${MODE}" == "full" ]]; then
  (
    cd backend
    BACKGROUND_WORKERS_ENABLED=true ../backend/.venv/bin/python -m celery -A app.workers.celery_app worker --loglevel=info
  ) &

  (
    cd backend
    BACKGROUND_WORKERS_ENABLED=true ../backend/.venv/bin/python -m celery -A app.workers.celery_app beat --loglevel=info
  ) &
else
  echo "Lean mode leaves workers disabled. Use 'make dev-full' to run worker and beat."
fi

(
  cd frontend
  NODE_OPTIONS="${NODE_OPTIONS}" npm run dev -- --hostname 0.0.0.0 --port "${FRONTEND_PORT}"
) &

wait
