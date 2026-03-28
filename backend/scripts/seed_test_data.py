#!/usr/bin/env python3
"""
seed_test_data.py — Deterministic staging/test seed data generator.

Usage:
  python scripts/seed_test_data.py          # Insert seed data
  python scripts/seed_test_data.py --reset  # Delete existing seed data then reinsert

SAFETY: Will refuse to run against a production database unless
        ENV=production is NOT set and ALLOW_SEED_IN_PROD is not set.
"""
import os
import sys
import uuid
import argparse
from datetime import datetime

# Guard: never run in production automatically
if os.environ.get("ENV") == "production" and not os.environ.get("ALLOW_SEED_IN_PROD"):
    print("❌  Refusing to seed production environment. Set ALLOW_SEED_IN_PROD=1 to override.")
    sys.exit(1)

# Add the backend app to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models.campaign import Contact, Campaign, CampaignLead
from app.models.monitoring import (
    WorkerHeartbeat, JobLog, SystemAlert, AuditLog, DeliverabilityEvent
)

DB_URL = os.environ.get(
    "POSTGRES_URL",
    os.environ.get("TEST_DATABASE_URL", "postgresql://user:password@localhost:5432/cold_email_test"),
)

engine = create_engine(DB_URL)
Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)


def reset(session):
    """Delete seed data rows identifiable by source tag."""
    session.query(CampaignLead).delete()
    session.query(Campaign).filter(Campaign.name.like("SEED:%")).delete()
    session.query(Contact).filter(Contact.source == "seed_script").delete()
    session.query(SystemAlert).filter(SystemAlert.source == "seed_script").delete()
    session.query(AuditLog).filter(AuditLog.metadata_blob["source"].as_string() == "seed_script").delete()
    session.query(WorkerHeartbeat).filter(WorkerHeartbeat.worker_name.like("seed-%")).delete()
    session.commit()
    print("✅  Seed data reset complete.")


def seed(session):
    # ── Contacts ─────────────────────────────────────────────────────────
    contacts = [
        Contact(id=uuid.uuid4(), email="valid1@example.com", first_name="Alice", company="ACME", verification_score=95, is_suppressed=False, is_disposable=False, source="seed_script"),
        Contact(id=uuid.uuid4(), email="valid2@example.com", first_name="Bob", company="Globex", verification_score=90, is_suppressed=False, is_disposable=False, source="seed_script"),
        Contact(id=uuid.uuid4(), email="risky@mailinator.com", first_name="Charlie", company="Disposable Co", verification_score=20, is_suppressed=False, is_disposable=True, source="seed_script"),
        Contact(id=uuid.uuid4(), email="invalid-email-no-mx", first_name=None, company=None, verification_score=5, is_suppressed=False, source="seed_script"),
        Contact(id=uuid.uuid4(), email="suppressed@bounced.com", first_name="Dave", company="Gone Corp", verification_score=0, is_suppressed=True, source="seed_script"),
    ]
    session.add_all(contacts)
    session.flush()
    print(f"  ✔  {len(contacts)} contacts seeded")

    # ── Campaigns ────────────────────────────────────────────────────────
    safe_campaign = Campaign(
        id=uuid.uuid4(), name="SEED: Safe Outreach Q1",
        template_subject="Let's connect!", template_body="Hi {{first_name}},\n\nWe'd love to chat.",
        status="draft", daily_limit=50,
    )
    blocked_campaign = Campaign(
        id=uuid.uuid4(), name="SEED: Blocked Unsafe Campaign",
        template_subject="Spammy Subject", template_body="Click now!",
        status="paused", daily_limit=500,
    )
    session.add_all([safe_campaign, blocked_campaign])
    session.flush()
    print("  ✔  2 campaigns seeded (1 safe, 1 blocked)")

    # ── Worker Heartbeats ────────────────────────────────────────────────
    workers = [
        WorkerHeartbeat(worker_name="seed-celery-1", worker_type="celery", status="healthy", last_seen_at=datetime.utcnow()),
        WorkerHeartbeat(worker_name="seed-celery-2", worker_type="celery", status="healthy", last_seen_at=datetime.utcnow()),
    ]
    session.add_all(workers)
    print("  ✔  2 worker heartbeats seeded")

    # ── Job Logs ─────────────────────────────────────────────────────────
    jobs = [
        JobLog(job_id=str(uuid.uuid4()), job_type="csv_import", status="completed", retry_count=0),
        JobLog(job_id=str(uuid.uuid4()), job_type="email_verify", status="failed", retry_count=2, error_message="DNS timeout"),
        JobLog(job_id=str(uuid.uuid4()), job_type="campaign_send", status="dead_letter", retry_count=5, error_message="SMTP refused"),
    ]
    session.add_all(jobs)
    print("  ✔  3 job logs seeded")

    # ── System Alerts ────────────────────────────────────────────────────
    alerts = [
        SystemAlert(alert_type="smtp_health_failed", severity="critical", title="SMTP Connection Failure", message="Mailcow SMTP relay did not respond within 5s.", source="seed_script", is_active=True),
        SystemAlert(alert_type="bounce_rate_high", severity="warning", title="High Bounce Rate", message="Bounce rate exceeded 8% on mailbox dev@example.com", source="seed_script", is_active=True),
    ]
    session.add_all(alerts)
    print("  ✔  2 system alerts seeded")

    # ── Audit Logs ───────────────────────────────────────────────────────
    audit_entries = [
        AuditLog(action="login", entity_type="user", metadata_blob={"source": "seed_script", "ip": "127.0.0.1"}),
        AuditLog(action="campaign_started", entity_type="campaign", entity_id=safe_campaign.id, metadata_blob={"source": "seed_script"}),
        AuditLog(action="suppression_added", entity_type="suppression_list", metadata_blob={"source": "seed_script", "email": "suppressed@bounced.com"}),
    ]
    session.add_all(audit_entries)
    print("  ✔  3 audit log entries seeded")

    session.commit()
    print("\n✅  All seed data inserted successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed test data")
    parser.add_argument("--reset", action="store_true", help="Delete existing seed data before inserting")
    args = parser.parse_args()

    with Session() as session:
        if args.reset:
            reset(session)
        seed(session)
