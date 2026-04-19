# Internal Testing Guide

This guide is for the self-hosted/internal version. It focuses on proving real runtime behavior before any SaaS work.

## Run The App

Use the normal development stack:

```bash
./scripts/dev.sh
```

Verify these surfaces before testing sends:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`
- Settings runtime: `/settings`
- Ops health: `/ops`

Worker-backed behavior requires the backend, Redis/broker, worker, and scheduler/beat to be running. If `/settings` or `/ops` says workers are disabled or unhealthy, campaign, inbox, and warm-up automation will not be trustworthy.

## Campaign Testing Checklist

Before starting a campaign:

- Open `/campaigns` and run `Dry Run`.
- Confirm the selected mailbox and sender identity are correct.
- Confirm at least one lead is eligible now.
- Confirm deliverability blockers are not present.
- Confirm suppression, contact type, verification, and compliance checks are not blocking every lead.

When testing execution:

- Use `Run pass now` for a single worker-backed campaign pass.
- Do not expect it to bypass eligibility, suppression, schedule, compliance, or deliverability checks.
- Inspect `Execution` on the campaign card for last queued, started, completed, send attempt, and current blocker state.
- If a job failed, use the retry action after fixing the blocker.

## Inbox Testing Checklist

Before relying on replies:

- Confirm the mailbox has IMAP details configured.
- For Google Workspace mailboxes, confirm OAuth is connected.
- Run provider diagnostics from `/mailboxes`.
- Open `/inbox` and run manual sync globally or per mailbox.
- Confirm empty states explain the real blocker if no messages appear.

Duplicate syncs should not create duplicate messages. Unmatched replies should still appear in the inbox even if campaign/contact linkage is unknown.

## Warm-Up Testing Checklist

Before warm-up can send:

- Global warm-up must be enabled.
- Workers must be healthy.
- At least two mailboxes must have warm-up enabled.
- At least two warm-up-enabled mailboxes must be SMTP/provider healthy.

Use `/warmup`:

- `Start Warm-up` enables global warm-up and queues an immediate pass when possible.
- `Run now` queues one manual worker-backed pass for internal testing.
- `Pause All` pauses global warm-up without deleting pairs or logs.

Warm-up logs should show `queued`, `success`, `skipped`, or `failed` with an operational reason.

## Google Workspace Checklist

For a Google Workspace mailbox:

- Provider must be enabled in `/settings`.
- Backend OAuth environment variables must be configured.
- Connect OAuth from the mailbox provider panel.
- After callback, the mailbox should show `connected`.
- Run provider check to validate SMTP XOAUTH2 and IMAP XOAUTH2.
- If status is `expired`, `error`, or `not_connected`, reconnect from the same panel.

Tokens and secrets must remain backend-only. The UI should only show safe status, last refresh time, expiry time, external account email, and error summaries.

## Mailcow Checklist

For a Mailcow mailbox:

- Provider must be enabled in `/settings`.
- Mailcow API health should be healthy or honestly degraded.
- SMTP diagnostics should pass before campaign or warm-up sending.
- IMAP diagnostics should pass before inbox sync is trusted.

Mailcow API health does not prove SMTP readiness. Always check SMTP separately.

## Smoke Command

Run:

```bash
scripts/internal_smoke_check.sh
```

Optional environment variables:

- `BACKEND_URL`, default `http://localhost:8000`
- `FRONTEND_URL`, default `http://localhost:3000`
- `AUTH_TOKEN`, bearer token for protected backend endpoints

The smoke check does not prove live delivery. It verifies route availability and gives fast feedback about health, settings, deliverability, warm-up, inbox, and campaigns endpoints.
