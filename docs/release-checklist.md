# Release Checklist — Cold Email CRM

> Run this before every production push. Mark each item ✅ or ❌. Include notes where relevant.

---

## Core Business Flow

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | Login with admin credentials works at `/signin` | ☐ | |
| 2 | Protected routes redirect unauthenticated users | ☐ | |
| 3 | Domain creation form submits and records appear | ☐ | |
| 4 | Mailbox creation stores mailbox credentials server-side only and never returns them in API responses | ☐ | |
| 5 | SMTP connectivity test for a mailbox returns healthy | ☐ | |
| 6 | IMAP sync triggers and messages appear in inbox | ☐ | |
| 7 | Warm-up can be started and stopped for a mailbox | ☐ | |
| 8 | Campaign creation and template saving works | ☐ | |
| 9 | Preflight blocks launch when suppressed leads exist | ☐ | |
| 10 | Suppressed contact is blocked from active campaign send | ☐ | |
| 11 | Inbox thread view loads and displays messages | ☐ | |
| 12 | AI Summarize action produces output or degrades gracefully | ☐ | |
| 13 | CSV import flow: upload → preview → confirm persists contacts | ☐ | |
| 14 | Email verification assigns trust score (0-100) | ☐ | |

---

## Ops & Monitoring

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 15 | `/ops` dashboard loads — health cards render | ☐ | |
| 16 | `/api/v1/ops/health` returns `healthy` status for DB | ☐ | |
| 17 | `/api/v1/ops/health/redis` returns `healthy` | ☐ | |
| 18 | `/api/v1/ops/health/workers` is `disabled` in lean mode or `healthy` in full mode | ☐ | |
| 18a | `/api/v1/ops/health/mailcow` returns a safe status payload | ☐ | |
| 19 | `/ops/jobs` shows job logs table | ☐ | |
| 20 | Failed job retry button changes status to `queued` | ☐ | |
| 21 | `/ops/alerts` renders active alerts list | ☐ | |
| 22 | Alert can be acknowledged | ☐ | |
| 23 | `/ops/deliverability` renders KPI cards | ☐ | |
| 24 | Audit logs appear at `/api/v1/ops/audit-logs` | ☐ | |

---

## Safety & Deliverability

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 25 | Invalid email rows rejected during CSV import | ☐ | |
| 26 | `is_suppressed` contacts never appear in campaign dispatches | ☐ | |
| 27 | Daily send limit enforced — jobs deferred when exceeded | ☐ | |
| 28 | Hard bounce auto-suppresses the contact | ☐ | |
| 29 | Unsubscribe keyword in reply triggers suppression | ☐ | |
| 30 | SPF/DKIM warning appears in preflight results | ☐ | |

---

## Deployment Readiness

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 31 | `alembic upgrade head` runs without errors | ☐ | |
| 32 | `SECRET_KEY` is set and non-default | ☐ | |
| 33 | `DEBUG=false` in production container | ☐ | |
| 34 | `/api/v1/ops/readiness` reports the expected structured state for the chosen mode (`degraded` in lean mode is acceptable if Mailcow or workers are intentionally blocked) | ☐ | |
| 35 | HTTPS termination configured at Nginx/proxy layer | ☐ | |
| 36 | `ALLOWED_ORIGINS` contains only production domains | ☐ | |
| 37 | Postgres backup schedule verified | ☐ | |
| 38 | Mailcow DKIM/SPF/DMARC records validated in DNS | ☐ | |

---

## Test Evidence

- Playwright report: `artifacts/playwright/index.html`
- pytest JUnit: `artifacts/pytest/results.xml`
- Coverage: `artifacts/pytest/coverage.xml`
