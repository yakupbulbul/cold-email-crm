# AI-Powered Cold Email CRM

Cold outreach CRM built with Next.js, FastAPI, PostgreSQL, Redis, Celery, and Mailcow.

The local development model is:

- local frontend -> local backend
- local backend -> local Postgres / Redis
- local backend -> remote Mailcow
- Mailcow credentials stay server-side in local `.env`

## Local Development

### Prerequisites

- Docker Desktop or another working Docker daemon
- Python 3.11+
- Node.js 20+

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
- `POSTGRES_PORT`
- `REDIS_PORT`
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

### 3. Start local infrastructure

```bash
make up
```

This starts only local Postgres and Redis for hybrid development.

The tracked defaults use dedicated Docker host ports so the app does not silently connect to another local Postgres or Redis instance:

- Postgres: `127.0.0.1:55432`
- Redis: `127.0.0.1:56379`

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

This runs:

- FastAPI on `BACKEND_URL`
- Celery worker on the host
- Celery beat on the host
- Next.js on `http://localhost:3000` by default

Sign in locally at `/signin`.

## Make Targets

```bash
make setup
make up
make down
make migrate
make bootstrap-admin
make seed
make dev
make smoke
make test
make reset
make full-up
make full-down
```

Notes:

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

The admin health endpoint for Mailcow is:

```text
/api/v1/ops/health/mailcow
```

The readiness endpoint includes Mailcow connectivity state:

```text
/api/v1/ops/readiness
```

If `MAILCOW_SMTP_HOST` and `MAILCOW_IMAP_HOST` are configured server-side, mailbox creation can omit explicit host fields and use those defaults automatically.

## Testing

### Backend

Database-backed backend tests expect the isolated test services from `docker-compose.test.yml`.

```bash
make test-infra-up
make test-backend
make test-infra-down
```

DB-free backend checks can run without Docker:

```bash
cd backend
../backend/.venv/bin/python -m pytest tests/api/test_config.py tests/api/test_mailcow.py -v
```

### Frontend

Focused frontend auth/runtime checks:

```bash
make test-frontend
```

Playwright E2E:

```bash
make test-e2e
```

## Troubleshooting

### Docker daemon is not running

Symptom:

- `make up` or `make test-infra-up` fails immediately

Fix:

- Start Docker Desktop or your Docker service
- rerun the command

### Backend fails on startup with config validation errors

Symptom:

- app refuses to boot because env values are missing or placeholders are still in use

Fix:

- set a real `SECRET_KEY`
- set `BOOTSTRAP_ADMIN_PASSWORD`
- ensure `MAILCOW_API_URL` and `MAILCOW_API_KEY` are either both set or both empty

### Frontend cannot reach backend

Symptom:

- sign-in fails
- dashboard shows backend connection errors

Fix:

- confirm backend is running on `BACKEND_URL`
- keep `NEXT_PUBLIC_API_URL=/api/v1`
- keep frontend pointed at the local backend, not Mailcow directly

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
