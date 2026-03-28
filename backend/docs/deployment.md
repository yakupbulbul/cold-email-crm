# Production Deployment Guide

## Core Architecture
This system operates universally above the Mailcow Stack. Mailcow exclusively handles outbound relay signatures (DKIM / SPF) alongside inbound IMAP routing. The Application stack only handles state machine scheduling and telemetry dashboards.

## Docker Environment Boundaries
Ensure the following variables are strictly mounted upon Production rollout:
- `SECRET_KEY`: Complex randomized JWT signing signature securely rotating token access logic.
- `POSTGRES_URL`: Physical location resolving structured tracking states.
- `REDIS_URL`: Queuing interface bridging standard FASTAPI states towards transient background operations smoothly.
- `OPENAI_API_KEY`: Strictly required for AI Warmup reply generations.

## Restore Policies & Snapshots
When resolving complete cluster failures, initiate a baseline `docker-compose up -d postgres`. Restore mapping limits explicitly using standard Postgres Dump artifacts ensuring full Contact state persistence. Transient Payload tracking and Worker jobs stored in Redis do not require backups as they are self-healing.
