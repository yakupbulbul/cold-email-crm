# Manual QA Runbook — Cold Email CRM

> For each step: perform the **action**, verify the **expected result**, mark ✅/❌, and add notes.

---

## 1. Authentication

| Step | Action | Expected Result | ✅/❌ | Notes |
|------|--------|----------------|-------|-------|
| 1.1 | Navigate to `/signin` | Login form displayed | | |
| 1.2 | Submit invalid credentials | Error message shown, no redirect | | |
| 1.3 | Submit valid admin credentials | Redirect to dashboard | | |
| 1.4 | Navigate to `/domains` while logged out (new window) | Redirect to `/signin` | | |
| 1.5 | Click logout (if available) | Session cleared, redirect to `/signin` | | |

---

## 2. Domain & Mailbox Setup

| Step | Action | Expected Result | ✅/❌ | Notes |
|------|--------|----------------|-------|-------|
| 2.1 | Go to `/domains`, click Add Domain | Domain creation form opens | | |
| 2.2 | Submit an invalid domain name (e.g. `not@domain`) | Validation error shown | | |
| 2.3 | Submit a valid domain (e.g. `qa-test.example.com`) | Domain appears in list | | |
| 2.4 | Go to `/mailboxes`, click Add Mailbox | Mailbox creation form opens | | |
| 2.5 | Submit mailbox without SMTP/IMAP hosts and without server defaults configured | Validation error shown | | |
| 2.6 | Submit valid mailbox credentials | Mailbox appears in list and no passwords are echoed back in the API response | | |

---

## 3. Warm-up

| Step | Action | Expected Result | ✅/❌ | Notes |
|------|--------|----------------|-------|-------|
| 3.1 | Go to `/warmup` | Warm-up list or empty state renders | | |
| 3.2 | In lean mode, click Start Warm-up for a mailbox | Clear `409` / safe-mode message explains that `make dev-full` is required | | |
| 3.3 | In full mode, click Start Warm-up | Status changes to active | | |
| 3.4 | Verify health score card displays | Score (0-100) visible | | |

---

## 4. Inbox

| Step | Action | Expected Result | ✅/❌ | Notes |
|------|--------|----------------|-------|-------|
| 4.1 | Go to `/inbox` | Thread list or empty state renders | | |
| 4.2 | Click a thread (if present) | Message detail view opens | | |
| 4.3 | Click AI Summarize (if visible) | Summary text appears or graceful error | | |
| 4.4 | Open reply composer | Reply textarea opens | | |

---

## 5. Campaigns

| Step | Action | Expected Result | ✅/❌ | Notes |
|------|--------|----------------|-------|-------|
| 5.1 | Go to `/campaigns`, click New | Campaign form opens | | |
| 5.2 | Submit with empty subject | Validation error shown | | |
| 5.3 | Create a valid campaign | Campaign appears in list | | |
| 5.4 | Trigger preflight on a campaign with suppressed leads | Preflight fails, launch blocked | | |
| 5.5 | Trigger preflight on a clean campaign | Shows pass/warning results | | |
| 5.6 | In lean mode, start a campaign | Clear `409` / safe-mode message explains that `make dev-full` is required | | |
| 5.7 | In full mode, pause an active campaign | Status changes to paused | | |

---

## 6. Contacts & CSV Import

| Step | Action | Expected Result | ✅/❌ | Notes |
|------|--------|----------------|-------|-------|
| 6.1 | Go to `/contacts` | Contact table or empty state visible | | |
| 6.2 | Go to `/contacts/import` | CSV dropzone visible | | |
| 6.3 | Upload a CSV with a mix of valid/invalid emails | Preview shows invalid row flags | | |
| 6.4 | Confirm import | Valid contacts saved, invalid rows rejected | | |

---

## 7. Email Verification

| Step | Action | Expected Result | ✅/❌ | Notes |
|------|--------|----------------|-------|-------|
| 7.1 | POST `/api/v1/leads/verify` with `mailinator.com` email | `is_disposable: true`, low score | | |
| 7.2 | POST `/api/v1/leads/verify` with `support@example.com` | `is_role_based: true` | | |
| 7.3 | POST `/api/v1/leads/verify` with valid business email | Score ≥ 80, `mx_valid: true` | | |

---

## 8. Suppression

| Step | Action | Expected Result | ✅/❌ | Notes |
|------|--------|----------------|-------|-------|
| 8.1 | Go to `/suppression` | Table or empty state visible | | |
| 8.2 | Add a new suppression entry | Entry appears in table | | |
| 8.3 | Attempt to send to suppressed email via campaign preflight | Lead flagged, launch blocked | | |
| 8.4 | Remove suppression (if allowed by role) | Entry removed | | |

---

## 9. Ops Dashboard

| Step | Action | Expected Result | ✅/❌ | Notes |
|------|--------|----------------|-------|-------|
| 9.1 | Go to `/ops` in lean mode | Status cards render for DB, Redis, Workers | | |
| 9.2 | Worker card shows `disabled` in lean mode or `healthy` in full mode | Status color and label are honest | | |
| 9.3 | Go to `/ops/jobs` | Job table renders (may be empty) | | |
| 9.4 | Go to `/ops/alerts` | Alert list or "all clear" message visible | | |
| 9.5 | Go to `/ops/deliverability` | KPI cards and mailbox table visible | | |
| 9.6 | Go to `/ops/readiness` | Checklist cards render | | |
| 9.7 | GET `/api/v1/ops/health/mailcow` as admin | Safe Mailcow health payload returned without exposing credentials | | |

---

## 10. Responsive UI

| Step | Action | Expected Result | ✅/❌ | Notes |
|------|--------|----------------|-------|-------|
| 10.1 | Open `/` at 375px width (iPhone SE) | Layout reflows without horizontal scroll | | |
| 10.2 | Sidebar or menu accessible on mobile | Navigation usable on narrow viewport | | |
| 10.3 | Campaign table readable on tablet (768px) | No overflow clipping | | |

---

## 11. Deployment Readiness

| Step | Action | Expected Result | ✅/❌ | Notes |
|------|--------|----------------|-------|-------|
| 11.1 | GET `/api/v1/ops/readiness` | Structured status plus checklist items; lean mode may be degraded and Mailcow auth may still fail safely | | |
| 11.2 | Verify `SECRET_KEY` is not the default test value | Strong random string in env | | |
| 11.3 | Verify `alembic upgrade head` shows no pending migrations | `Running upgrade ... done` | | |
| 11.4 | Confirm HTTPS terminates at proxy, HTTP redirects cleanly | `curl -I http://...` returns 301 | | |
