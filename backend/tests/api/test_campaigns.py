"""test_campaigns.py — Campaign API + preflight tests."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from app.models.campaign import Campaign, CampaignLead, Contact, SendLog
from app.models.core import Domain, Mailbox
from app.models.lists import CampaignList, LeadList, LeadListMember
from app.models.monitoring import JobLog
from app.services.campaign_service import CampaignService
from app.services.smtp_service import SMTPServiceError


def test_list_campaigns_returns_200_or_401(client: TestClient):
    resp = client.get("/api/v1/campaigns")
    assert resp.status_code in (200, 401)


def test_create_campaign_missing_fields_returns_422(client: TestClient):
    resp = client.post("/api/v1/campaigns", json={})
    assert resp.status_code in (400, 401, 422)


def test_campaign_preflight_endpoint_exists(client: TestClient):
    # Use a dummy UUID — 404 or 401 acceptable, not 500
    resp = client.post("/api/v1/campaigns/00000000-0000-0000-0000-000000000000/preflight")
    assert resp.status_code in (200, 401, 404)


def test_campaign_preflight_history_endpoint_exists(client: TestClient):
    resp = client.get("/api/v1/campaigns/00000000-0000-0000-0000-000000000000/preflight/history")
    assert resp.status_code in (200, 401, 404)


def test_start_campaign_requires_background_workers(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.campaigns.settings.BACKGROUND_WORKERS_ENABLED", False)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-workers.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-workers.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Lean Mode Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )

    resp = client.post(f"/api/v1/campaigns/{campaign_resp.json()['id']}/start", headers=auth_headers)
    assert resp.status_code == 409
    assert "make dev or make dev-full" in resp.json()["detail"]


def test_start_campaign_requires_scheduled_lead(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.campaigns.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-start.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-start.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Needs Leads",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )

    resp = client.post(f"/api/v1/campaigns/{campaign_resp.json()['id']}/start", headers=auth_headers)
    assert resp.status_code == 409
    assert "scheduled, eligible lead" in resp.json()["detail"]


def test_start_campaign_queues_job_when_lead_exists(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.campaigns.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    queued_campaign_ids: list[str] = []

    def _queue_task(campaign_id: str):
        queued_campaign_ids.append(campaign_id)
        return type("Task", (), {"id": "campaign-job-1"})()

    monkeypatch.setattr("app.api.v1.routes.campaigns.run_campaign_cycle.delay", _queue_task)

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-queue.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-queue.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Queued Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Hi {{first_name}}",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )

    contact = Contact(
        email="lead@example.com",
        first_name="Lead",
        email_status="valid",
        verification_score=100,
        verification_integrity="high",
        is_suppressed=False,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    db.add(CampaignLead(campaign_id=campaign_resp.json()["id"], contact_id=contact.id, status="scheduled"))
    db.commit()

    resp = client.post(f"/api/v1/campaigns/{campaign_resp.json()['id']}/start", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["job_queued"] is True
    assert payload["eligible_leads"] == 1
    assert payload["status"] == "queued"
    assert queued_campaign_ids == [campaign_resp.json()["id"]]


def test_start_campaign_returns_503_when_queue_submit_fails(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.campaigns.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    def _raise_queue_failure(campaign_id: str):
        raise RuntimeError("redis down")

    monkeypatch.setattr("app.api.v1.routes.campaigns.run_campaign_cycle.delay", _raise_queue_failure)

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-queue-fail.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-queue-fail.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Queue Failure Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Hi {{first_name}}",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )

    contact = Contact(
        email="lead-queue-fail@example.com",
        first_name="Lead",
        email_status="valid",
        verification_score=100,
        verification_integrity="high",
        is_suppressed=False,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    db.add(CampaignLead(campaign_id=campaign_resp.json()["id"], contact_id=contact.id, status="scheduled"))
    db.commit()

    resp = client.post(f"/api/v1/campaigns/{campaign_resp.json()['id']}/start", headers=auth_headers)
    assert resp.status_code == 503
    assert "could not be queued" in str(resp.json()["detail"]).lower()

    campaign = db.query(Campaign).filter(Campaign.id == campaign_resp.json()["id"]).first()
    assert campaign.status == "draft"


def test_pause_campaign_updates_status(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-pause.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-pause.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Pause Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )
    campaign_id = campaign_resp.json()["id"]
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    campaign.status = "active"
    db.commit()

    resp = client.post(f"/api/v1/campaigns/{campaign_id}/pause", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


def test_list_campaigns_ignores_stale_queued_job_in_execution_summary(client: TestClient, auth_headers: dict, db, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.campaigns.settings.BACKGROUND_WORKERS_ENABLED", True)

    domain = Domain(name="summary.example.com")
    db.add(domain)
    db.commit()
    db.refresh(domain)

    mailbox = Mailbox(
        domain_id=domain.id,
        email="sender@summary.example.com",
        display_name="Sender",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="sender@summary.example.com",
        smtp_password_encrypted="enc",
        smtp_security_mode="starttls",
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="sender@summary.example.com",
        imap_password_encrypted="enc",
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)

    campaign = Campaign(
        name="Summary State Campaign",
        mailbox_id=mailbox.id,
        template_subject="Subject",
        template_body="Body",
        daily_limit=10,
        status="active",
        campaign_type="b2b",
        compliance_mode="standard",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    stale_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
    db.add(
        JobLog(
            job_id="stale-queued-job",
            job_type="campaign_cycle",
            status="queued",
            payload_summary={"campaign_id": str(campaign.id)},
            created_at=stale_time,
        )
    )
    db.add(
        JobLog(
            job_id="recent-completed-job",
            job_type="campaign_cycle",
            status="completed",
            payload_summary={"campaign_id": str(campaign.id)},
            created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1),
            started_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1),
            finished_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=30),
        )
    )
    db.commit()

    resp = client.get("/api/v1/campaigns", headers=auth_headers)
    assert resp.status_code == 200
    payload = next(item for item in resp.json() if item["id"] == str(campaign.id))
    assert payload["execution_summary"]["state"] == "waiting_for_beat"
    assert payload["execution_summary"]["detail"] == "No job is running right now. The next automatic campaign pass will be queued by beat."


def test_list_campaigns_includes_last_delivery_attempt_in_execution_summary(client: TestClient, auth_headers: dict, db, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.campaigns.settings.BACKGROUND_WORKERS_ENABLED", True)

    domain = Domain(name="delivery-summary.example.com")
    db.add(domain)
    db.commit()
    db.refresh(domain)

    mailbox = Mailbox(
        domain_id=domain.id,
        email="sender@delivery-summary.example.com",
        display_name="Sender",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="sender@delivery-summary.example.com",
        smtp_password_encrypted="enc",
        smtp_security_mode="starttls",
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="sender@delivery-summary.example.com",
        imap_password_encrypted="enc",
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)

    campaign = Campaign(
        name="Delivery Attempt Summary Campaign",
        mailbox_id=mailbox.id,
        template_subject="Subject",
        template_body="Body",
        daily_limit=10,
        status="active",
        campaign_type="b2c",
        compliance_mode="standard",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    db.add(
        SendLog(
            mailbox_id=mailbox.id,
            campaign_id=campaign.id,
            target_email="lead@example.com",
            subject="Subject",
            delivery_status="failed",
            smtp_response="timed out",
        )
    )
    db.commit()

    resp = client.get("/api/v1/campaigns", headers=auth_headers)
    assert resp.status_code == 200
    payload = next(item for item in resp.json() if item["id"] == str(campaign.id))
    assert payload["execution_summary"]["last_delivery_status"] == "failed"
    assert payload["execution_summary"]["last_delivery_target_email"] == "lead@example.com"
    assert payload["execution_summary"]["last_delivery_error"] == "timed out"


def test_delete_campaign_removes_draft_campaign(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-delete.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-delete.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Delete Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )
    campaign_id = campaign_resp.json()["id"]

    delete_resp = client.delete(f"/api/v1/campaigns/{campaign_id}", headers=auth_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "deleted"
    assert db.query(Campaign).filter(Campaign.id == campaign_id).first() is None


def test_delete_campaign_blocks_non_draft_campaign(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-non-draft.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-non-draft.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Blocked Delete Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )
    campaign_id = campaign_resp.json()["id"]
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    campaign.status = "paused"
    db.commit()

    delete_resp = client.delete(f"/api/v1/campaigns/{campaign_id}", headers=auth_headers)
    assert delete_resp.status_code == 409
    assert "Only draft campaigns can be deleted" in delete_resp.json()["detail"]


def test_archive_campaign_updates_non_draft_status(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-archive.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-archive.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Archive Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )
    campaign_id = campaign_resp.json()["id"]
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    campaign.status = "paused"
    db.commit()

    archive_resp = client.post(f"/api/v1/campaigns/{campaign_id}/archive", headers=auth_headers)
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "archived"
    db.refresh(campaign)
    assert campaign.status == "archived"


def test_start_campaign_blocks_archived_campaign(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.campaigns.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-archived-start.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-archived-start.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Archived Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )
    campaign_id = campaign_resp.json()["id"]
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    campaign.status = "archived"
    db.commit()

    resp = client.post(f"/api/v1/campaigns/{campaign_id}/start", headers=auth_headers)
    assert resp.status_code == 409
    assert "Archived campaigns cannot be started" in resp.json()["detail"]


def test_unarchive_campaign_restores_archived_to_paused(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-unarchive.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-unarchive.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Unarchive Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )
    campaign_id = campaign_resp.json()["id"]
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    campaign.status = "archived"
    db.commit()

    restore_resp = client.post(f"/api/v1/campaigns/{campaign_id}/unarchive", headers=auth_headers)
    assert restore_resp.status_code == 200
    assert restore_resp.json()["status"] == "paused"
    db.refresh(campaign)
    assert campaign.status == "paused"


def test_unarchive_campaign_blocks_non_archived_records(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-unarchive-block.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-unarchive-block.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Non Archived Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )

    restore_resp = client.post(f"/api/v1/campaigns/{campaign_resp.json()['id']}/unarchive", headers=auth_headers)
    assert restore_resp.status_code == 409
    assert "Only archived campaigns can be restored" in restore_resp.json()["detail"]


def test_list_campaigns_marks_archived_execution_state(client: TestClient, auth_headers: dict, db):
    domain = Domain(name="campaign-archive-summary.example.com")
    db.add(domain)
    db.commit()
    db.refresh(domain)

    mailbox = Mailbox(
        domain_id=domain.id,
        email="sender@campaign-archive-summary.example.com",
        display_name="Sender",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="sender@campaign-archive-summary.example.com",
        smtp_password_encrypted="enc",
        smtp_security_mode="starttls",
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="sender@campaign-archive-summary.example.com",
        imap_password_encrypted="enc",
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)

    campaign = Campaign(
        name="Archived Summary Campaign",
        mailbox_id=mailbox.id,
        template_subject="Subject",
        template_body="Body",
        daily_limit=10,
        status="archived",
    )
    db.add(campaign)
    db.commit()

    resp = client.get("/api/v1/campaigns", headers=auth_headers)
    assert resp.status_code == 200
    payload = next(item for item in resp.json() if item["id"] == str(campaign.id))
    assert payload["status"] == "archived"
    assert payload["execution_summary"]["state"] == "archived"


def test_delete_campaign_returns_404_for_missing_record(client: TestClient, auth_headers: dict):
    delete_resp = client.delete("/api/v1/campaigns/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert delete_resp.status_code == 404


def test_create_campaign_persists_b2c_fields(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-b2c.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-b2c.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Newsletter Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2c",
            "channel_type": "email",
            "goal_type": "newsletter",
            "list_strategy": "list_based",
            "compliance_mode": "strict_b2c",
            "send_window_timezone": "Europe/Berlin",
        },
        headers=auth_headers,
    )
    assert campaign_resp.status_code == 200
    payload = campaign_resp.json()
    assert payload["campaign_type"] == "b2c"
    assert payload["goal_type"] == "newsletter"
    assert payload["compliance_mode"] == "strict_b2c"
    assert payload["send_window_timezone"] == "Europe/Berlin"


def test_b2c_strict_campaign_excludes_unknown_consent_and_type_mismatch(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.campaigns.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.campaigns.run_campaign_cycle.delay", lambda campaign_id: type("Task", (), {"id": "campaign-job-2"})())

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-b2c-strict.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-b2c-strict.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Strict B2C Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Hi",
            "daily_limit": 10,
            "campaign_type": "b2c",
            "compliance_mode": "strict_b2c",
            "goal_type": "newsletter",
        },
        headers=auth_headers,
    )
    campaign_id = campaign_resp.json()["id"]

    allowed = Contact(
        email="consumer@example.com",
        email_status="valid",
        verification_score=95,
        verification_integrity="high",
        contact_type="b2c",
        consent_status="granted",
        unsubscribe_status="subscribed",
    )
    blocked_unknown = Contact(
        email="unknown@example.com",
        email_status="valid",
        verification_score=95,
        verification_integrity="high",
        contact_type="b2c",
        consent_status="unknown",
        unsubscribe_status="subscribed",
    )
    mismatched = Contact(
        email="b2b@example.com",
        email_status="valid",
        verification_score=95,
        verification_integrity="high",
        contact_type="b2b",
        consent_status="granted",
        unsubscribe_status="subscribed",
    )
    db.add_all([allowed, blocked_unknown, mismatched])
    db.commit()
    db.refresh(allowed)
    db.refresh(blocked_unknown)
    db.refresh(mismatched)

    db.add_all([
        CampaignLead(campaign_id=campaign_id, contact_id=allowed.id, status="scheduled"),
        CampaignLead(campaign_id=campaign_id, contact_id=blocked_unknown.id, status="scheduled"),
        CampaignLead(campaign_id=campaign_id, contact_id=mismatched.id, status="scheduled"),
    ])
    db.commit()

    preflight_resp = client.post(f"/api/v1/campaigns/{campaign_id}/preflight", headers=auth_headers)
    assert preflight_resp.status_code == 200
    preflight = preflight_resp.json()
    assert preflight["audience_summary"]["consent_unknown_count"] == 1
    assert preflight["audience_summary"]["type_mismatch_count"] == 1
    assert any(check["name"] == "b2c_compliance" for check in preflight["checks"])

    start_resp = client.post(f"/api/v1/campaigns/{campaign_id}/start", headers=auth_headers)
    assert start_resp.status_code == 200
    assert start_resp.json()["eligible_leads"] == 1


def test_start_campaign_resyncs_attached_lists_after_lead_becomes_eligible(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.campaigns.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    queued_campaign_ids: list[str] = []

    def _queue_task(campaign_id: str):
        queued_campaign_ids.append(campaign_id)
        return type("Task", (), {"id": "campaign-job-resync"})()

    monkeypatch.setattr("app.api.v1.routes.campaigns.run_campaign_cycle.delay", _queue_task)

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-resync.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-resync.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Resync Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )
    campaign_id = campaign_resp.json()["id"]

    lead = Contact(
        email="late-verified@example.com",
        first_name="Late",
        email_status="unverified",
        verification_score=None,
        verification_integrity=None,
        is_suppressed=False,
        contact_type="b2b",
        unsubscribe_status="subscribed",
        consent_status="unknown",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    lead_list = LeadList(name="Late Eligible Leads", description="Test list")
    db.add(lead_list)
    db.commit()
    db.refresh(lead_list)
    db.add(LeadListMember(list_id=lead_list.id, lead_id=lead.id))
    db.add(CampaignList(campaign_id=campaign_id, list_id=lead_list.id))
    db.commit()

    blocked_resp = client.post(f"/api/v1/campaigns/{campaign_id}/start", headers=auth_headers)
    assert blocked_resp.status_code == 409

    lead.email_status = "valid"
    lead.verification_score = 100
    lead.verification_integrity = "high"
    db.add(lead)
    db.commit()

    start_resp = client.post(f"/api/v1/campaigns/{campaign_id}/start", headers=auth_headers)
    assert start_resp.status_code == 200
    assert start_resp.json()["eligible_leads"] == 1
    assert queued_campaign_ids == [campaign_id]

    scheduled = db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign_id, CampaignLead.contact_id == lead.id).first()
    assert scheduled is not None
    assert scheduled.status == "scheduled"


def test_start_campaign_reschedules_failed_list_leads_when_still_eligible(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.campaigns.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.campaigns.run_campaign_cycle.delay", lambda campaign_id: type("Task", (), {"id": "campaign-job-retry"})())

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-retry.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-retry.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Retry Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2c",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )
    campaign_id = campaign_resp.json()["id"]

    lead = Contact(
        email="retry@example.com",
        first_name="Retry",
        email_status="valid",
        verification_score=100,
        verification_integrity="high",
        is_suppressed=False,
        contact_type="b2c",
        consent_status="unknown",
        unsubscribe_status="subscribed",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    lead_list = LeadList(name="Retry Leads", description="Retry list")
    db.add(lead_list)
    db.commit()
    db.refresh(lead_list)
    db.add(LeadListMember(list_id=lead_list.id, lead_id=lead.id))
    db.add(CampaignList(campaign_id=campaign_id, list_id=lead_list.id))
    db.commit()

    failed_row = CampaignLead(campaign_id=campaign_id, contact_id=lead.id, status="failed")
    db.add(failed_row)
    db.commit()

    start_resp = client.post(f"/api/v1/campaigns/{campaign_id}/start", headers=auth_headers)
    assert start_resp.status_code == 200
    assert start_resp.json()["eligible_leads"] == 1

    refreshed = db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign_id, CampaignLead.contact_id == lead.id).first()
    assert refreshed is not None
    assert refreshed.status == "scheduled"


def test_list_campaigns_includes_execution_summary(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.campaigns.settings.BACKGROUND_WORKERS_ENABLED", True)

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-execution.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-execution.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    client.post(
        "/api/v1/campaigns",
        json={
            "name": "Execution Summary Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 10,
            "campaign_type": "b2b",
            "compliance_mode": "standard",
        },
        headers=auth_headers,
    )

    resp = client.get("/api/v1/campaigns", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    campaign = next(item for item in payload if item["name"] == "Execution Summary Campaign")
    assert campaign["execution_summary"]["state"] == "idle"
    assert campaign["execution_summary"]["beat_interval_seconds"] == 300
    assert campaign["execution_summary"]["detail"]


def test_update_campaign_persists_fields(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "campaign-edit.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@campaign-edit.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "Editable Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Old Subject",
            "template_body": "Old Body",
            "daily_limit": 10,
        },
        headers=auth_headers,
    )
    campaign_id = campaign_resp.json()["id"]

    update_resp = client.put(
        f"/api/v1/campaigns/{campaign_id}",
        json={
            "name": "Updated Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "New Subject",
            "template_body": "New Body",
            "daily_limit": 25,
        },
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    payload = update_resp.json()
    assert payload["name"] == "Updated Campaign"
    assert payload["template_subject"] == "New Subject"
    assert payload["template_body"] == "New Body"
    assert payload["daily_limit"] == 25

    refreshed = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    assert refreshed.name == "Updated Campaign"
    assert refreshed.template_subject == "New Subject"
    assert refreshed.template_body == "New Body"
    assert refreshed.daily_limit == 25


def test_campaign_processing_marks_lead_failed_when_smtp_times_out(db):
    domain = Domain(name="smtp-failure-test.example.com")
    db.add(domain)
    db.commit()
    db.refresh(domain)

    mailbox = Mailbox(
        domain_id=domain.id,
        email="sender@smtp-failure-test.example.com",
        display_name="Sender",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="sender@smtp-failure-test.example.com",
        smtp_password_encrypted="super-secret-password",
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="sender@smtp-failure-test.example.com",
        imap_password_encrypted="super-secret-password",
        status="active",
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)

    contact = Contact(
        email="smtp-fail@example.com",
        first_name="SMTP",
        email_status="valid",
        verification_score=100,
        verification_integrity="high",
        consent_status="granted",
        unsubscribe_status="subscribed",
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    campaign = Campaign(
        name="SMTP Failure Campaign",
        status="active",
        mailbox_id=mailbox.id,
        template_subject="Hello {{first_name}}",
        template_body="Hi {{first_name}}",
        daily_limit=10,
        campaign_type="b2b",
        compliance_mode="standard",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    lead = CampaignLead(campaign_id=campaign.id, contact_id=contact.id, status="scheduled")
    db.add(lead)
    db.commit()

    service = CampaignService(db)

    service.smtp.provider.send_email = lambda **kwargs: (False, "timed out")  # type: ignore[method-assign]
    result = service.process_campaign_by_id(str(campaign.id))

    assert result["processed"] == 1
    failed_lead = db.query(CampaignLead).filter(CampaignLead.id == lead.id).first()
    assert failed_lead.status == "failed"
    failed_log = db.query(SendLog).filter(SendLog.campaign_id == campaign.id, SendLog.contact_id == contact.id).first()
    assert failed_log is not None
    assert failed_log.delivery_status == "failed"


def test_campaign_processing_reschedules_failed_list_leads_on_next_cycle(db):
    domain = Domain(name="retry-cycle.example.com")
    db.add(domain)
    db.commit()
    db.refresh(domain)

    mailbox = Mailbox(
        domain_id=domain.id,
        email="sender@retry-cycle.example.com",
        display_name="Sender",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="sender@retry-cycle.example.com",
        smtp_password_encrypted="enc",
        smtp_security_mode="starttls",
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="sender@retry-cycle.example.com",
        imap_password_encrypted="enc",
        status="active",
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)

    campaign = Campaign(
        name="Retry Cycle Campaign",
        mailbox_id=mailbox.id,
        template_subject="Hi {{first_name}}",
        template_body="Hello {{first_name}}",
        daily_limit=10,
        status="active",
        campaign_type="b2c",
        compliance_mode="standard",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    lead_list = LeadList(name="Retry Cycle List", description="Retry members", type="static")
    db.add(lead_list)
    db.commit()
    db.refresh(lead_list)
    db.add(CampaignList(campaign_id=campaign.id, list_id=lead_list.id))

    contact = Contact(
        email="retry@example.com",
        first_name="Retry",
        contact_type="b2c",
        email_status="valid",
        verification_score=100,
        verification_integrity="high",
        is_suppressed=False,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    db.add(LeadListMember(list_id=lead_list.id, lead_id=contact.id))
    db.commit()

    failed_lead = CampaignLead(campaign_id=campaign.id, contact_id=contact.id, status="failed")
    db.add(failed_lead)
    db.commit()

    service = CampaignService(db)
    service.smtp = type(
        "StubSMTP",
        (),
        {"send_email": lambda self, req: (True, f"<retry@example.com>|{uuid4()}")},
    )()

    processed = service.process_campaign_by_id(str(campaign.id))
    assert processed["processed"] == 1

    refreshed = db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign.id, CampaignLead.contact_id == contact.id).first()
    assert refreshed is not None
    assert refreshed.status == "sent"


def test_campaign_processing_does_not_count_failed_logs_against_daily_limit(db):
    domain = Domain(name="daily-limit-failed.example.com")
    db.add(domain)
    db.commit()
    db.refresh(domain)

    mailbox = Mailbox(
        domain_id=domain.id,
        email="sender@daily-limit-failed.example.com",
        display_name="Sender",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="sender@daily-limit-failed.example.com",
        smtp_password_encrypted="enc",
        smtp_security_mode="starttls",
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="sender@daily-limit-failed.example.com",
        imap_password_encrypted="enc",
        status="active",
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)

    contact = Contact(
        email="limit-check@example.com",
        first_name="Limit",
        contact_type="b2c",
        email_status="valid",
        verification_score=100,
        verification_integrity="high",
        is_suppressed=False,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)

    campaign = Campaign(
        name="Failed Logs Limit Campaign",
        mailbox_id=mailbox.id,
        template_subject="Hi {{first_name}}",
        template_body="Hello {{first_name}}",
        daily_limit=1,
        status="active",
        campaign_type="b2c",
        compliance_mode="standard",
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    db.add(CampaignLead(campaign_id=campaign.id, contact_id=contact.id, status="scheduled"))
    db.add(
        SendLog(
            mailbox_id=mailbox.id,
            campaign_id=campaign.id,
            contact_id=contact.id,
            target_email=contact.email,
            subject="Previous failed attempt",
            delivery_status="failed",
            smtp_response="timed out",
        )
    )
    db.commit()

    service = CampaignService(db)
    service.smtp = type(
        "StubSMTP",
        (),
        {"send_email": lambda self, req: (True, f"<limit@example.com>|{uuid4()}")},
    )()

    result = service.process_campaign_by_id(str(campaign.id))
    assert result["processed"] == 1

    refreshed = db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign.id, CampaignLead.contact_id == contact.id).first()
    assert refreshed is not None
    assert refreshed.status == "sent"
