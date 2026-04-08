"""test_campaigns.py — Campaign API + preflight tests."""
import pytest
from fastapi.testclient import TestClient
from app.models.campaign import Campaign, CampaignLead, Contact


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
        },
        headers=auth_headers,
    )

    resp = client.post(f"/api/v1/campaigns/{campaign_resp.json()['id']}/start", headers=auth_headers)
    assert resp.status_code == 409
    assert "make dev-full" in resp.json()["detail"]


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
        },
        headers=auth_headers,
    )

    resp = client.post(f"/api/v1/campaigns/{campaign_resp.json()['id']}/start", headers=auth_headers)
    assert resp.status_code == 409
    assert "scheduled, verified, unsuppressed lead" in resp.json()["detail"]


def test_start_campaign_queues_job_when_lead_exists(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.campaigns.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.campaigns.run_campaign_cycle.delay", lambda: type("Task", (), {"id": "campaign-job-1"})())

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

    paused_campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    assert paused_campaign.status == "paused"
