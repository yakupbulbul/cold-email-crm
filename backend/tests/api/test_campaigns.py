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

    paused_campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    assert paused_campaign.status == "paused"


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
    monkeypatch.setattr("app.api.v1.routes.campaigns.run_campaign_cycle.delay", lambda: type("Task", (), {"id": "campaign-job-2"})())

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
