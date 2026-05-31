# Production Deployment Guide

## Core Architecture
This system uses Google Workspace as the sole mail provider via OAuth/XOAUTH2 for both SMTP sending and IMAP inbox sync. The application stack handles state machine scheduling, campaign management, and telemetry dashboards.

## Docker Environment Boundaries
Ensure the following variables are strictly mounted upon Production rollout:
- `SECRET_KEY`: Complex randomized JWT signing signature securely rotating token access logic.
- `POSTGRES_URL`: Physical location resolving structured tracking states.
- `REDIS_URL`: Queuing interface bridging standard FASTAPI states towards transient background operations smoothly.
- `GOOGLE_WORKSPACE_CLIENT_ID`: OAuth client ID for Google Workspace integration.
- `GOOGLE_WORKSPACE_CLIENT_SECRET`: OAuth client secret for Google Workspace integration.
- `GOOGLE_WORKSPACE_REDIRECT_URI`: OAuth redirect URI for Google Workspace callback.

## Restore Policies & Snapshots
When resolving complete cluster failures, initiate a baseline `docker-compose up -d postgres`. Restore mapping limits explicitly using standard Postgres Dump artifacts ensuring full Contact state persistence. Transient Payload tracking and Worker jobs stored in Redis do not require backups as they are self-healing.
