#!/usr/bin/env bash
set -u

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"
AUTH_HEADER=()

if [ -n "${AUTH_TOKEN:-}" ]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${AUTH_TOKEN}")
fi

check_url() {
  local label="$1"
  local method="$2"
  local url="$3"
  local expected="$4"
  local code

  if [ "$method" = "POST" ] && [ ${#AUTH_HEADER[@]} -gt 0 ]; then
    code="$(curl -sS -L -o /tmp/internal_smoke_body.json -w "%{http_code}" -X POST "${AUTH_HEADER[@]}" "$url")"
  elif [ "$method" = "POST" ]; then
    code="$(curl -sS -L -o /tmp/internal_smoke_body.json -w "%{http_code}" -X POST "$url")"
  elif [ ${#AUTH_HEADER[@]} -gt 0 ]; then
    code="$(curl -sS -L -o /tmp/internal_smoke_body.json -w "%{http_code}" "${AUTH_HEADER[@]}" "$url")"
  else
    code="$(curl -sS -L -o /tmp/internal_smoke_body.json -w "%{http_code}" "$url")"
  fi

  if [[ "$code" =~ ^(${expected})$ ]]; then
    printf "PASS %-28s %s\n" "$label" "$code"
  else
    printf "FAIL %-28s got %s expected %s\n" "$label" "$code" "$expected"
    sed -n '1,4p' /tmp/internal_smoke_body.json
  fi
}

printf "Internal smoke check\n"
printf "Frontend: %s\n" "$FRONTEND_URL"
printf "Backend:  %s\n\n" "$BACKEND_URL"

check_url "frontend root" "GET" "$FRONTEND_URL" "200"
check_url "backend health" "GET" "$BACKEND_URL/api/v1/health/" "200"

if [ -z "${AUTH_TOKEN:-}" ]; then
  printf "\nAUTH_TOKEN not set. Protected endpoint checks will expect 401/403.\n"
  check_url "settings summary protected" "GET" "$BACKEND_URL/api/v1/settings/summary" "401|403"
else
  printf "\nAUTH_TOKEN set. Checking protected operational endpoints.\n"
  check_url "settings summary" "GET" "$BACKEND_URL/api/v1/settings/summary" "200"
  check_url "deliverability overview" "GET" "$BACKEND_URL/api/v1/deliverability/overview" "200"
  check_url "warmup status" "GET" "$BACKEND_URL/api/v1/warmup/status" "200"
  check_url "inbox status" "GET" "$BACKEND_URL/api/v1/inbox/status" "200"
  check_url "campaign list" "GET" "$BACKEND_URL/api/v1/campaigns" "200"
fi
