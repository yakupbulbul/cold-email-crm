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
: "${NODE_OPTIONS:=--max-old-space-size=1024}"
: "${DEV_LOG_DIR:=tmp/dev-logs}"
: "${NEXT_DEV_BUNDLER:=webpack}"
: "${UVICORN_LOG_LEVEL:=warning}"
: "${CELERY_LOGLEVEL:=warning}"
: "${CELERY_WORKER_CONCURRENCY:=1}"
: "${CELERY_WORKER_POOL:=solo}"

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
mkdir -p "${DEV_LOG_DIR}"

BACKEND_LOG="${DEV_LOG_DIR}/backend.log"
FRONTEND_LOG="${DEV_LOG_DIR}/frontend.log"
WORKER_LOG="${DEV_LOG_DIR}/worker.log"
BEAT_LOG="${DEV_LOG_DIR}/beat.log"

echo "Starting host development mode: ${MODE}"
echo "Backend:  ../backend/.venv/bin/python -m uvicorn app.main:app --reload --reload-dir app --host ${BACKEND_HOST} --port ${BACKEND_PORT} --log-level ${UVICORN_LOG_LEVEL}"
echo "Frontend: cd frontend && NODE_OPTIONS='${NODE_OPTIONS}' npm run dev -- --${NEXT_DEV_BUNDLER} --hostname 0.0.0.0 --port ${FRONTEND_PORT}"
echo "Worker:   cd backend && ../backend/.venv/bin/python -m celery -A app.workers.celery_app worker --loglevel=${CELERY_LOGLEVEL} --pool=${CELERY_WORKER_POOL} --concurrency=${CELERY_WORKER_CONCURRENCY}"
echo "Beat:     cd backend && ../backend/.venv/bin/python -m celery -A app.workers.celery_app beat --loglevel=${CELERY_LOGLEVEL}"
echo "Logs:     ${BACKEND_LOG} ${FRONTEND_LOG} ${WORKER_LOG} ${BEAT_LOG}"

: > "${BACKEND_LOG}"
: > "${FRONTEND_LOG}"
: > "${WORKER_LOG}"
: > "${BEAT_LOG}"

(
  cd backend
  BACKGROUND_WORKERS_ENABLED="${BACKGROUND_WORKERS_ENABLED_VALUE}" ../backend/.venv/bin/python -m uvicorn app.main:app --reload --reload-dir app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" --log-level "${UVICORN_LOG_LEVEL}" >> "../${BACKEND_LOG}" 2>&1
) &

if [[ "${MODE}" == "full" ]]; then
  (
    cd backend
    BACKGROUND_WORKERS_ENABLED=true ../backend/.venv/bin/python -m celery -A app.workers.celery_app worker --loglevel="${CELERY_LOGLEVEL}" --pool="${CELERY_WORKER_POOL}" --concurrency="${CELERY_WORKER_CONCURRENCY}" >> "../${WORKER_LOG}" 2>&1
  ) &

  (
    cd backend
    BACKGROUND_WORKERS_ENABLED=true ../backend/.venv/bin/python -m celery -A app.workers.celery_app beat --loglevel="${CELERY_LOGLEVEL}" >> "../${BEAT_LOG}" 2>&1
  ) &
else
  echo "Lean mode leaves workers disabled. Use 'make dev-full' to run worker and beat."
fi

(
  cd frontend
  NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS="${NODE_OPTIONS}" npm run dev -- --"${NEXT_DEV_BUNDLER}" --hostname 0.0.0.0 --port "${FRONTEND_PORT}" >> "../${FRONTEND_LOG}" 2>&1
) &

sleep 2
echo "Ready checks:"
echo "  Backend URL:  http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "  Frontend URL: http://localhost:${FRONTEND_PORT}"
echo "Use 'tail -f ${BACKEND_LOG}' or 'tail -f ${FRONTEND_LOG}' for live logs."

wait
