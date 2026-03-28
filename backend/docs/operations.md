# Cold Email CRM - Operator Manual

## System Health & Telemetry
The Operations Dashboard (`/ops`) provides a real-time aggregate of standard API pings reaching core components:
1. **PostgreSQL Check**: Verifies read/write query latencies over the primary database mapped inside `docker-compose`.
2. **Redis Backplane Check**: Resolves persistent socket connections mapping queued states natively.
3. **SMTP/IMAP Engine Link**: Resolves raw port availability confirming outbound relay connections explicitly mapping the Mailcow interface.

## Background Worker Reliability (Job Queues)
Extensive CSV ingestion protocols and Verifier tasks operate via Celery workflows async. You can monitor, halt, or violently retry tasks explicitly in the Ops Jobs panel (`/ops/jobs`). Background workers possess idempotent payloads natively; halting a task midway retains mapped rows predictably.

## Global Suppression and Blacklisting
The Deliverability Engine (`/ops/deliverability`) maps live stream aggregates resolving Hard Bounces. Any Bounce strictly triggers a hard flag migrating the prospect entirely to the Global Suppression List natively. Attempting to inject a queued Campaign sequence upon a globally suppressed email address forcibly triggers the Campaign Preflight Checker, removing the Lead permanently from the outbound sequence.
