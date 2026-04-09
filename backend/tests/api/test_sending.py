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
    assert log.provider_message_id == "<message-id-1@example.com>"
    assert log.smtp_response == "<message-id-1@example.com>"
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    assert mailbox.smtp_last_check_status == "healthy"


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
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    assert mailbox.smtp_last_check_status == "failed"
    assert mailbox.smtp_last_check_category == "smtp_timeout"


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
    assert payload[0]["provider_message_id"] == "<message-id-logs@example.com>"


def test_provider_generates_rfc_message_id_when_missing():
    from app.integrations.smtp.provider import MailcowSMTPProvider

    captured = {}

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            self.sock = self

        def ehlo(self):
            return None

        def starttls(self, context=None):
            return None

        def settimeout(self, timeout):
            return None

        def login(self, username, password):
            return None

        def send_message(self, msg, from_addr=None, to_addrs=None):
            captured["message_id"] = msg.get("Message-ID")
            captured["from_header"] = msg.get("From")
            captured["envelope_from"] = from_addr
            return {}

        def quit(self):
            return None

    provider = MailcowSMTPProvider()

    import smtplib

    original_smtp = smtplib.SMTP
    smtplib.SMTP = FakeSMTP
    try:
        success, message_id = provider.send_email(
            host="smtp.example.com",
            port=587,
            username="sender@example.com",
            password="password",
            security_mode="starttls",
            sender_email="sender@example.com",
            from_header="Support Team <sender@example.com>",
            to_emails=["recipient@example.com"],
            subject="Generated id",
            text_body="Hello",
        )
    finally:
        smtplib.SMTP = original_smtp

    assert success is True
    assert message_id == captured["message_id"]
    assert message_id.startswith("<")
    assert message_id.endswith(">")
    assert "@example.com>" in message_id
    assert captured["from_header"] == "Support Team <sender@example.com>"
    assert captured["envelope_from"] == "sender@example.com"


def test_sender_identity_falls_back_to_raw_email_when_display_name_missing(db):
    from app.models.core import Mailbox
    from app.services.smtp_service import SMTPManagerService

    mailbox = Mailbox(
        email="sender@example.com",
        display_name="   ",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="sender@example.com",
        smtp_password_encrypted="password",
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="sender@example.com",
        imap_password_encrypted="password",
    )

    service = SMTPManagerService(db)
    assert service.build_sender_identity(mailbox) == "sender@example.com"
