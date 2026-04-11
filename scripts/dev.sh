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
: "${DEV_PID_DIR:=tmp/dev-pids}"
: "${NEXT_DEV_BUNDLER:=webpack}"
: "${UVICORN_LOG_LEVEL:=warning}"
: "${CELERY_LOGLEVEL:=warning}"
: "${CELERY_WORKER_CONCURRENCY:=1}"
: "${CELERY_WORKER_POOL:=solo}"
: "${BACKEND_RELOAD:=auto}"

resolve_bin() {
  local name="$1"
  shift
  local candidate
  if candidate="$(command -v "${name}" 2>/dev/null)"; then
    echo "${candidate}"
    return 0
  fi
  for candidate in "$@"; do
    if [[ -x "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done
  return 1
}

NODE_BIN="$(resolve_bin node \
  /opt/homebrew/bin/node \
  /usr/local/bin/node \
  "$HOME/.nvm/versions/node/v22.20.0/bin/node" \
  "$HOME/.nvm/versions/node/v20.19.2/bin/node" \
  "$HOME/.nvm/versions/node/v18.20.8/bin/node" \
  "$HOME/.nvm/versions/node/v18.20.4/bin/node")" || {
    echo "Missing node. Install Node.js or add it to PATH."
    exit 1
  }

NPM_BIN="$(resolve_bin npm \
  /opt/homebrew/bin/npm \
  /usr/local/bin/npm \
  "$HOME/.nvm/versions/node/v22.20.0/bin/npm" \
  "$HOME/.nvm/versions/node/v20.19.2/bin/npm" \
  "$HOME/.nvm/versions/node/v18.20.8/bin/npm" \
  "$HOME/.nvm/versions/node/v18.20.4/bin/npm")" || {
    echo "Missing npm. Install Node.js or add it to PATH."
    exit 1
  }

BACKGROUND_WORKERS_ENABLED_VALUE=false
if [[ "${MODE}" == "full" ]]; then
  BACKGROUND_WORKERS_ENABLED_VALUE=true
fi

if [[ "${BACKEND_RELOAD}" == "auto" ]]; then
  if [[ "${MODE}" == "full" ]]; then
    BACKEND_RELOAD=false
  else
    BACKEND_RELOAD=true
  fi
fi

if [[ ! -x backend/.venv/bin/python ]]; then
  echo "Missing backend/.venv. Run 'make setup' first."
  exit 1
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "Missing frontend/node_modules. Run 'make setup' first."
  exit 1
fi

mkdir -p "${DEV_LOG_DIR}"
mkdir -p "${DEV_PID_DIR}"

BACKEND_LOG="${DEV_LOG_DIR}/backend.log"
FRONTEND_LOG="${DEV_LOG_DIR}/frontend.log"
WORKER_LOG="${DEV_LOG_DIR}/worker.log"
BEAT_LOG="${DEV_LOG_DIR}/beat.log"
BACKEND_PID_FILE="${DEV_PID_DIR}/backend.pid"
FRONTEND_PID_FILE="${DEV_PID_DIR}/frontend.pid"
WORKER_PID_FILE="${DEV_PID_DIR}/worker.pid"
BEAT_PID_FILE="${DEV_PID_DIR}/beat.pid"

cleanup_pid_file() {
  local pid_file="$1"
  if [[ -f "${pid_file}" ]]; then
    local existing_pid
    existing_pid="$(<"${pid_file}")"
    if [[ -n "${existing_pid}" ]] && kill -0 "${existing_pid}" 2>/dev/null; then
      kill "${existing_pid}" 2>/dev/null || true
      sleep 1
      kill -9 "${existing_pid}" 2>/dev/null || true
    fi
    rm -f "${pid_file}"
  fi
}

cleanup_managed_processes() {
  cleanup_pid_file "${BACKEND_PID_FILE}"
  cleanup_pid_file "${FRONTEND_PID_FILE}"
  cleanup_pid_file "${WORKER_PID_FILE}"
  cleanup_pid_file "${BEAT_PID_FILE}"
}

cleanup_children() {
  cleanup_managed_processes
}

trap cleanup_children EXIT INT TERM
cleanup_managed_processes
setopt local_options null_glob
rm -f backend/celerybeat-schedule.db backend/celerybeat-schedule.db.* 2>/dev/null || true

BACKEND_CMD=(../backend/.venv/bin/python -m uvicorn app.main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" --log-level "${UVICORN_LOG_LEVEL}")
if [[ "${BACKEND_RELOAD}" == "true" ]]; then
  BACKEND_CMD=(../backend/.venv/bin/python -m uvicorn app.main:app --reload --reload-dir app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" --log-level "${UVICORN_LOG_LEVEL}")
fi

DISPLAY_MODE="${MODE}"
if [[ "${MODE}" == "lean" ]]; then
  DISPLAY_MODE="low-ram"
fi

echo "Starting host development mode: ${DISPLAY_MODE}"
echo "Backend:  ${BACKEND_CMD[*]}"
echo "Frontend: cd frontend && NODE_OPTIONS='${NODE_OPTIONS}' ${NPM_BIN} run dev -- --${NEXT_DEV_BUNDLER} --hostname 0.0.0.0 --port ${FRONTEND_PORT}"
echo "Worker:   cd backend && ../backend/.venv/bin/python -m celery -A app.workers.celery_app worker --loglevel=${CELERY_LOGLEVEL} --pool=${CELERY_WORKER_POOL} --concurrency=${CELERY_WORKER_CONCURRENCY}"
echo "Beat:     cd backend && ../backend/.venv/bin/python -m scripts.dev_scheduler"
echo "Logs:     ${BACKEND_LOG} ${FRONTEND_LOG} ${WORKER_LOG} ${BEAT_LOG}"

: > "${BACKEND_LOG}"
: > "${FRONTEND_LOG}"
: > "${WORKER_LOG}"
: > "${BEAT_LOG}"

(
  cd backend
  BACKGROUND_WORKERS_ENABLED="${BACKGROUND_WORKERS_ENABLED_VALUE}" "${BACKEND_CMD[@]}" >> "../${BACKEND_LOG}" 2>&1
) &
echo $! > "${BACKEND_PID_FILE}"

if [[ "${MODE}" == "full" ]]; then
  (
    cd backend
    BACKGROUND_WORKERS_ENABLED=true ../backend/.venv/bin/python -m celery -A app.workers.celery_app worker --loglevel="${CELERY_LOGLEVEL}" --pool="${CELERY_WORKER_POOL}" --concurrency="${CELERY_WORKER_CONCURRENCY}" >> "../${WORKER_LOG}" 2>&1
  ) &
  echo $! > "${WORKER_PID_FILE}"

  (
    cd backend
    BACKGROUND_WORKERS_ENABLED=true ../backend/.venv/bin/python -m scripts.dev_scheduler >> "../${BEAT_LOG}" 2>&1
  ) &
  echo $! > "${BEAT_PID_FILE}"
else
  echo "Low-RAM mode leaves workers disabled. Use 'make dev' or 'make dev-full' to run worker and beat."
fi

(
  cd frontend
  PATH="$(dirname "${NODE_BIN}"):${PATH}" NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS="${NODE_OPTIONS}" "${NPM_BIN}" run dev -- --"${NEXT_DEV_BUNDLER}" --hostname 0.0.0.0 --port "${FRONTEND_PORT}" >> "../${FRONTEND_LOG}" 2>&1
) &
echo $! > "${FRONTEND_PID_FILE}"

sleep 2
echo "Ready checks:"
echo "  Backend URL:  http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "  Frontend URL: http://localhost:${FRONTEND_PORT}"
if [[ "${MODE}" == "full" ]]; then
  echo "  Worker mode:  enabled (campaigns and warmup can run)"
else
  echo "  Worker mode:  disabled (campaigns and warmup stay read-only)"
fi
echo "Use 'tail -f ${BACKEND_LOG}' or 'tail -f ${FRONTEND_LOG}' for live logs."

wait
