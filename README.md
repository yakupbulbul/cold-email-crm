# AI-Powered Cold Email CRM

Cold outreach CRM built with Next.js, FastAPI, PostgreSQL, Redis, Celery, and Mailcow.

The local development model is:

- local frontend -> local backend
- local backend -> local Postgres / Redis
- local backend -> remote Mailcow
- Mailcow credentials stay server-side in local `.env`

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 20+
- Homebrew on macOS for the recommended host Redis install

Recommended host-run services:

- PostgreSQL on `127.0.0.1:5432`
- Redis on `127.0.0.1:6379`

Docker is optional fallback infrastructure. It is no longer required for the default local workflow.

### 1. Clone and create local env

```bash
git clone https://github.com/yakupbulbul/cold-email-crm.git
cd cold-email-crm
cp .env.example .env
```

Use your private local setup reference to fill in real values in `.env`.

Rules:

- Never commit `.env`
- Never copy secrets into tracked files
- Keep `README_PRIVATE.md` local-only
- Use placeholders only in tracked docs and examples

Required local values:

- `SECRET_KEY`
- `BOOTSTRAP_ADMIN_PASSWORD`
- `POSTGRES_URL`
- `REDIS_URL`
- `ALLOWED_ORIGINS`
- `MAILCOW_API_URL` and `MAILCOW_API_KEY` if you want live remote Mailcow checks

Optional:

- `OPENAI_API_KEY`
- `MAILCOW_SMTP_HOST`, `MAILCOW_SMTP_PORT`
- `MAILCOW_IMAP_HOST`, `MAILCOW_IMAP_PORT`

### 2. Install host dependencies

```bash
make setup
```

This creates `backend/.venv` and installs frontend dependencies.

### 3. Install and verify host services

```bash
brew install redis
brew services start redis
make host-check
```

`make host-check` validates the current `.env` against the host Postgres and Redis endpoints before the app starts.

The tracked defaults now target host services directly:

- Postgres: `127.0.0.1:5432`
- Redis: `127.0.0.1:6379`

If you prefer Docker-backed infra instead, keep Docker running and use:

```bash
make up
```

### 4. Run migrations and bootstrap local access

```bash
make migrate
make bootstrap-admin
```

`make bootstrap-admin` creates only the local admin from `.env`. It does not insert demo records.

If you explicitly want deterministic demo/test data later, run:

```bash
make seed
```

### 5. Run the app locally

```bash
make dev
```

`make dev` is the lean default. It runs:

- FastAPI on `BACKEND_URL`
- Next.js on `http://localhost:3000` by default

It also prints the exact host-run commands for backend, frontend, worker, and beat. Worker and beat are intentionally disabled in lean mode to reduce memory and process count.

When you need queue processing, use:

```bash
make dev-full
```

`make dev-full` starts backend, frontend, Celery worker, and Celery beat together on the host.

Sign in locally at `/signin`.

## Make Targets

```bash
make setup
make host-check
make up
make down
make migrate
make bootstrap-admin
make seed
make dev
make dev-full
make smoke
make test
make reset
make full-up
make full-down
```

Notes:

- `make host-check` is the default no-Docker preflight
- `make dev` is lean mode: backend + frontend only
- `make dev-full` enables Celery worker + beat on the host
- `make up` and `make reset` require Docker
- `make bootstrap-admin` is the primary no-seed login path
- `make full-up` runs the entire stack in Docker
- `make smoke` checks local backend, DB, and Redis endpoints
- `make test` runs backend tests plus focused frontend auth/runtime checks

## Mailcow Integration

This repo does not replace Mailcow.

Use the existing remote Mailcow instance by setting:

- `MAILCOW_API_URL`
- `MAILCOW_API_KEY`
- optional default SMTP / IMAP host values

Security boundaries:

- The frontend never receives Mailcow API keys
- The frontend only calls the local backend
- Mailcow API checks happen server-side only
- Mailbox credentials remain server-side and are never returned in API responses
- Use a read-only Mailcow API key for the default local workflow
- `MAILCOW_ENABLE_MUTATIONS=false` keeps the integration in safe mode by default

The admin health endpoint for Mailcow is:

```text
/api/v1/ops/health/mailcow
```

The readiness endpoint includes Mailcow connectivity state:

```text
/api/v1/ops/readiness
```

If `MAILCOW_SMTP_HOST` and `MAILCOW_IMAP_HOST` are configured server-side, mailbox creation can omit explicit host fields and use those defaults automatically.

### Domain Verification

Adding a domain does more than insert a local row.

The backend now:

- creates the local record first
- checks whether the domain exists in remote Mailcow
- runs DNS checks for `MX`, `SPF`, `DKIM`, and `DMARC`
- stores the verification result in the local DB
- computes an honest readiness state

Domain states:

- `pending`: verification has not finished yet
- `local_only`: stored locally but not verified in Mailcow
- `mailcow_verified`: found in Mailcow, but DNS is still incomplete
- `dns_partial`: some required DNS records are present, but not all
- `ready`: Mailcow verification passed and all required DNS checks passed
- `blocked`: verification could not complete safely, usually because Mailcow is unconfigured, unreachable, or unauthorized
- `failed`: verification ran but at least one check failed unexpectedly

The Domains UI exposes:

- overall status
- Mailcow verification status
- DNS status summary
- last checked time
- missing requirements
- `Verify`, `Refresh`, and `Details` actions

This means a domain is not treated as connected just because it exists in the local database.

## Testing

### Backend

Host-backed backend checks use `.env.test.local` and do not require Docker if local Postgres and Redis are running:

```bash
make test-backend
```

If you want isolated Docker-backed test services instead:

```bash
make test-infra-up
make test-backend
make test-infra-down
```

### Frontend

Lint and typed frontend test sources:

```bash
make test-frontend
```

Playwright E2E:

```bash
make test-e2e
```

Focused milestone suites:

```bash
make test-api
make test-e2e-auth
make test-e2e-ops
make test-e2e-empty
make test-e2e-boundary
make test-smoke
```

### Performance / k6

The repo now includes env-driven k6 suites under [performance/k6](/Users/yakupbulbul/Documents/codex/cold-mail/performance/k6):

- `smoke`: auth, domains, mailboxes, ops health
- `load`: sustained list/settings/health traffic
- `stress`: list + readiness pressure
- `soak`: auth/session and health stability

Install k6 locally first, for example:

```bash
brew install k6
```

Then run:

```bash
make test-load-smoke
make test-load-load
make test-load-stress
make test-load-soak
make test-load
```

All k6 suites are env-driven and use only safe read-only endpoints. They do not trigger Mailcow mutations.

### Release Readiness

Use the release-readiness workflow to run the milestone checks as one pass:

```bash
make test-release
```

This runs:

- auth / route protection coverage
- ops / settings coverage
- empty / error-state coverage
- boundary / secret-safety coverage
- backend API suite
- k6 smoke checks

## Troubleshooting

### Host Redis is missing

Symptom:

- `make host-check` fails on Redis
- `make dev` refuses to start

Fix:

- install Redis locally with `brew install redis`
- start it with `brew services start redis`
- rerun `make host-check`

### Docker daemon is not running

Symptom:

- `make up` or `make test-infra-up` fails immediately

Fix:

- Start Docker Desktop or your Docker service
- rerun the command if you are using Docker-backed infra

### Backend fails on startup with config validation errors

Symptom:

- app refuses to boot because env values are missing or placeholders are still in use

Fix:

- set a real `SECRET_KEY`
- set `BOOTSTRAP_ADMIN_PASSWORD`
- ensure `MAILCOW_API_URL` and `MAILCOW_API_KEY` are either both set or both empty

### Domain stays blocked after creation

Symptom:

- domain create succeeds
- status shows `blocked`
- Mailcow details mention unconfigured, unauthorized, or unreachable

Fix:

- confirm `MAILCOW_API_URL` points to the remote Mailcow API base URL
- confirm `MAILCOW_API_KEY` is a valid backend-only read-only key
- re-run verification from the Domains page or `POST /api/v1/domains/{id}/refresh`

### Domain is in Mailcow but not ready

Symptom:

- status shows `mailcow_verified` or `dns_partial`

Fix:

- add or correct the domain `MX`, `SPF`, `DKIM`, and `DMARC` DNS records
- rerun `Verify` or `Refresh` after DNS propagation

### Frontend cannot reach backend

Symptom:

- sign-in fails
- dashboard shows backend connection errors

Fix:

- confirm backend is running on `BACKEND_URL`
- keep `NEXT_PUBLIC_API_URL=/api/v1`
- keep frontend pointed at the local backend, not Mailcow directly

### Warmup or campaign start returns `409`

Symptom:

- warmup start says background workers are disabled
- campaign start says to run `make dev-full`

Fix:

- this is expected in lean mode
- run `make dev-full` when you need queue-backed processing

### Mailcow health is degraded or failed

Symptom:

- `/api/v1/ops/health/mailcow` reports `degraded` or `failed`

Fix:

- verify local `.env` has the correct remote Mailcow URL and API key
- confirm the remote API is reachable from your machine
- verify SSL settings if your environment requires a custom certificate path or disabled verification

## Security Checklist

- `.env` stays local and untracked
- `README_PRIVATE.md` stays ignored
- tracked docs use placeholders only
- Mailcow credentials are never exposed to the browser

## License

MIT
