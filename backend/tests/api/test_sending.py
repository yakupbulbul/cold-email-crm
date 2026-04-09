from fastapi.testclient import TestClient

from app.models.campaign import SendLog
from app.models.core import Mailbox


def _mailbox_payload(domain_id: str, email: str) -> dict:
    return {
        "domain_id": domain_id,
        "email": email,
        "display_name": "Sender",
        "smtp_password": "super-secret-password",
        "imap_password": "super-secret-password",
    }


def _create_active_mailbox(client: TestClient, auth_headers: dict, monkeypatch, domain_name: str, email: str) -> str:
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    domain_resp = client.post("/api/v1/domains", json={"name": domain_name}, headers=auth_headers)
    mailbox_resp = client.post("/api/v1/mailboxes", json=_mailbox_payload(domain_resp.json()["id"], email), headers=auth_headers)
    return mailbox_resp.json()["id"]


def test_send_email_sends_immediately_and_logs_attempt(client: TestClient, auth_headers: dict, monkeypatch, db):
    mailbox_id = _create_active_mailbox(
        client,
        auth_headers,
        monkeypatch,
        "send-email-success.example.com",
        "sender@send-email-success.example.com",
    )
    monkeypatch.setattr(
        "app.services.smtp_service.MailcowSMTPProvider.send_email",
        lambda self, **kwargs: (True, "<message-id-1@example.com>"),
    )

    resp = client.post(
        "/api/v1/send-email",
        json={
            "mailbox_id": mailbox_id,
            "to": ["recipient@example.com"],
            "subject": "Direct send",
            "text_body": "Hello",
            "html_body": "<p>Hello</p>",
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["success"] is True
    assert payload["status"] == "sent"
    assert payload["provider"] == "smtp"
    assert payload["message_id"] == "<message-id-1@example.com>"
    assert payload["log_id"]

    log = db.query(SendLog).filter(SendLog.id == payload["log_id"]).first()
    assert log is not None
    assert log.delivery_status == "success"
    assert log.target_email == "recipient@example.com"


def test_send_email_requires_active_mailbox(client: TestClient, auth_headers: dict, monkeypatch, db):
    mailbox_id = _create_active_mailbox(
        client,
        auth_headers,
        monkeypatch,
        "send-email-inactive.example.com",
        "sender@send-email-inactive.example.com",
    )
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    mailbox.status = "paused"
    db.commit()

    resp = client.post(
        "/api/v1/send-email",
        json={
            "mailbox_id": mailbox_id,
            "to": ["recipient@example.com"],
            "subject": "Direct send",
            "text_body": "Hello",
        },
        headers=auth_headers,
    )

    assert resp.status_code == 409
    assert resp.json()["detail"]["message"] == "Mailbox must be active before sending email."
    assert resp.json()["detail"]["category"] == "mailbox_inactive"


def test_send_email_returns_safe_failure_and_logs_attempt(client: TestClient, auth_headers: dict, monkeypatch, db):
    mailbox_id = _create_active_mailbox(
        client,
        auth_headers,
        monkeypatch,
        "send-email-fail.example.com",
        "sender@send-email-fail.example.com",
    )
    monkeypatch.setattr(
        "app.services.smtp_service.MailcowSMTPProvider.send_email",
        lambda self, **kwargs: (False, "Connection timed out while connecting to smtp.example.com"),
    )

    resp = client.post(
        "/api/v1/send-email",
        json={
            "mailbox_id": mailbox_id,
            "to": ["recipient@example.com"],
            "subject": "Direct send",
            "text_body": "Hello",
        },
        headers=auth_headers,
    )

    assert resp.status_code == 504
    assert resp.json()["detail"]["category"] == "smtp_timeout"
    assert "timed out" in resp.json()["detail"]["message"].lower()

    log = db.query(SendLog).filter(SendLog.mailbox_id == mailbox_id).order_by(SendLog.created_at.desc()).first()
    assert log is not None
    assert log.delivery_status == "failed"
    assert "timed out" in (log.smtp_response or "").lower()


def test_send_email_logs_endpoint_returns_recent_attempts(client: TestClient, auth_headers: dict, monkeypatch):
    mailbox_id = _create_active_mailbox(
        client,
        auth_headers,
        monkeypatch,
        "send-email-logs.example.com",
        "sender@send-email-logs.example.com",
    )
    monkeypatch.setattr(
        "app.services.smtp_service.MailcowSMTPProvider.send_email",
        lambda self, **kwargs: (True, "<message-id-logs@example.com>"),
    )

    client.post(
        "/api/v1/send-email",
        json={
            "mailbox_id": mailbox_id,
            "to": ["recipient@example.com"],
            "subject": "History send",
            "text_body": "Hello",
        },
        headers=auth_headers,
    )

    resp = client.get("/api/v1/send-email/logs?limit=5", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) >= 1
    assert payload[0]["target_email"] == "recipient@example.com"
