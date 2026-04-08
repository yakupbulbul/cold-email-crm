#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT_DIR}"

summary() {
  local label="$1"
  local status="$2"
  printf "%-28s %s\n" "${label}" "${status}"
}

run_step() {
  local label="$1"
  shift
  if "$@"; then
    summary "${label}" "PASS"
  else
    summary "${label}" "FAIL"
    return 1
  fi
}

echo "Release readiness validation"
echo

run_step "Auth / route coverage" make test-e2e-auth
run_step "Ops / settings coverage" make test-e2e-ops
run_step "Empty / error coverage" make test-e2e-empty
run_step "Boundary / secret checks" make test-e2e-boundary
run_step "Backend API suite" make test-api
run_step "k6 smoke" make test-load-smoke

echo
echo "Blocked by safe mode:"
echo "- Mailcow mutations remain disabled by default."
echo "- Worker-backed campaign and warmup execution require make dev-full."
