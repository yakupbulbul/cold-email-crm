# Cold Email CRM

Cold outreach CRM built with Next.js, FastAPI, PostgreSQL, Redis, and Celery.

## Unified B2B + B2C Model

This app is one shared outreach platform, not separate B2B and B2C products.

Shared primitives:

- contacts / leads
- reusable static lists
- campaigns
- verification and scoring
- suppression
- preflight and execution
- mailbox / domain infrastructure

Typed behavior:

- contacts can carry `contact_type`, consent, unsubscribe, company/persona, engagement, and tags
- campaigns can carry `campaign_type`, `goal_type`, `compliance_mode`, and reusable attached lists
- B2B campaigns allow risky contacts as warnings when otherwise eligible
- B2C campaigns apply stricter hygiene and compliance checks
- `strict_b2c` blocks contacts with unusable consent states such as `unknown`, `revoked`, or `unsubscribed`
- global suppression remains a universal blocker for both campaign types

Audience reuse:

- static lists are the primary reusable audience unit
- one contact can belong to multiple lists
- one campaign can attach multiple lists
- attached-list audiences are deduplicated before scheduling
- blocked contacts stay visible in summaries and preflight instead of being silently treated as healthy

The local development model is:

- local frontend -> local backend
- local backend -> local Postgres / Redis
- local backend -> Google Workspace via OAuth
- Google Workspace credentials stay server-side in local `.env`

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

Optional:

- `GOOGLE_WORKSPACE_CLIENT_ID` and `GOOGLE_WORKSPACE_CLIENT_SECRET` for OAuth mailbox setup
- `GOOGLE_WORKSPACE_SMTP_HOST` (defaults to `smtp.gmail.com`)
- `GOOGLE_WORKSPACE_IMAP_HOST` (defaults to `imap.gmail.com`)

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

`make dev` is the normal worker-enabled local runtime. It runs:

- FastAPI on `BACKEND_URL`
- Next.js on `http://localhost:3000` by default
- Celery worker on host
- Celery beat on host

It also prints the exact host-run commands for backend, frontend, worker, and beat.

If you want the lower-RAM backend+frontend-only workflow instead, use:

```bash
make dev-lean
```

`make dev-lean` keeps worker-backed flows unavailable on purpose. `make dev-full` remains available as a compatibility alias for the same worker-enabled runtime as `make dev`.

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
make dev-lean
make dev-full
make smoke
make test
make reset
make full-up
make full-down
```

Notes:

- `make host-check` is the default no-Docker preflight
- `make dev` is the default host runtime: backend + frontend + worker + beat
- `make dev-lean` is the low-RAM host runtime: backend + frontend only
- `make dev-full` is an alias for the worker-enabled host runtime
- `make up` and `make reset` require Docker
- `make bootstrap-admin` is the primary no-seed login path
- `make full-up` runs the entire stack in Docker
- `make smoke` checks local backend, DB, and Redis endpoints
- `make test` runs backend tests plus focused frontend auth/runtime checks

## Google Workspace Integration

Google Workspace is the sole mail provider. Mailboxes connect via OAuth and use XOAUTH2 for SMTP and IMAP.

Setup:

1. Configure a Google Cloud project with Gmail API enabled
2. Set `GOOGLE_WORKSPACE_CLIENT_ID` and `GOOGLE_WORKSPACE_CLIENT_SECRET` in `.env`
3. Add mailboxes in the UI and complete the OAuth consent flow

Security boundaries:

- OAuth tokens are stored server-side and never returned in API responses
- The frontend only calls the local backend, never Google APIs directly
- SMTP and IMAP connections use XOAUTH2 authentication

### Domain Verification

Adding a domain verifies DNS records only.

The backend:

- creates the local record
- runs DNS checks for `MX`, `SPF`, `DKIM`, and `DMARC`
- stores the verification result in the local DB
- computes an honest readiness state

Domain states:

- `pending`: verification has not finished yet
- `dns_partial`: some required DNS records are present, but not all
- `ready`: all required DNS checks passed
- `failed`: verification ran but at least one check failed unexpectedly

The Domains UI exposes:

- overall status
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

The repo includes env-driven k6 suites under [performance/k6](/Users/yakupbulbul/Documents/codex/cold-mail/performance/k6):

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

All k6 suites are env-driven and use only safe read-only endpoints.

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

### Domain stays in failed or dns_partial state

Symptom:

- domain create succeeds
- status shows `failed` or `dns_partial`

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
- keep frontend pointed at the local backend

### Warmup or campaign start returns `409`

Symptom:

- warmup start says background workers are disabled
- campaign start says to run `make dev-full`

Fix:

- this is expected only in `make dev-lean`
- restart with `make dev` or `make dev-full` when you need queue-backed processing

## Security Checklist

- `.env` stays local and untracked
- `README_PRIVATE.md` stays ignored
- tracked docs use placeholders only
- OAuth tokens are never exposed to the browser

## License

MIT
