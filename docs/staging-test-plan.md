# Staging Test Plan — Cold Email CRM

## Scope

This plan covers the automated and manual validation performed against the staging
environment before every production release.

## Environments

| Environment | URL | DB | SMTP/IMAP | AI |
|-------------|-----|----|-----------|----|
| local-dev | `http://localhost:3000` | dev postgres | Mailpit | disabled |
| staging | `https://staging.crm.example.com` | staging postgres | Mailpit / Mailcow staging | enabled |
| production | `https://crm.example.com` | prod postgres | Mailcow prod | enabled |

## Test Execution Matrix

| Layer | Tool | When | Command |
|-------|------|------|---------|
| API unit tests | pytest | Every PR, every merge | `make test-api` |
| Integration tests | pytest `-m integration` | Staging boot, release branch | `make test-integration` |
| E2E smoke | Playwright | Every merge to main | `make test-e2e-smoke` |
| E2E full | Playwright | Release branch push | `make test-e2e` |
| Full release | All of above | Before production push | `make test-release` |
| Manual QA | Human runbook | Every RC candidate | See `docs/manual-qa-runbook.md` |

## Boot Staging

```bash
cp .env.staging.example .env.staging
# edit .env.staging with real secrets
make staging-up
make seed-staging
PLAYWRIGHT_BASE_URL=http://localhost:3000 make test-release
```

## Artifact Locations

| Artifact | Path |
|----------|------|
| Playwright HTML report | `artifacts/playwright/index.html` |
| Playwright JUnit XML | `artifacts/playwright/results.xml` |
| pytest JUnit XML | `artifacts/pytest/results.xml` |
| Coverage XML | `artifacts/pytest/coverage.xml` |

## Pass Criteria

- All `test-api` pytest tests pass with 0 failures
- No Playwright test failures on the smoke suite
- `/api/v1/ops/readiness` returns `status: ready`
- Manual QA checklist has 0 ❌ items
