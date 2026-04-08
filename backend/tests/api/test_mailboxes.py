"""test_mailboxes.py — Mailbox endpoint coverage for host defaults and safe responses."""
from fastapi.testclient import TestClient


def test_create_mailbox_uses_server_side_defaults(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_PORT", 587)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_PORT", 993)

    domain_resp = client.post("/api/v1/domains", json={"name": "mailbox-test.example.com"}, headers=auth_headers)
    domain_id = domain_resp.json()["id"]

    payload = {
        "domain_id": domain_id,
        "email": "hello@mailbox-test.example.com",
        "display_name": "Hello",
        "smtp_password": "super-secret-password",
        "imap_password": "super-secret-password",
    }
    resp = client.post("/api/v1/mailboxes", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["smtp_host"] == "smtp.example.com"
    assert body["imap_host"] == "imap.example.com"
    assert "smtp_password" not in body
    assert "imap_password" not in body
    assert "smtp_password_encrypted" not in body
    assert "imap_password_encrypted" not in body


def test_create_mailbox_requires_hosts_without_server_defaults(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", None)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", None)

    domain_resp = client.post("/api/v1/domains", json={"name": "manual-hosts.example.com"}, headers=auth_headers)
    domain_id = domain_resp.json()["id"]

    payload = {
        "domain_id": domain_id,
        "email": "hello@manual-hosts.example.com",
        "display_name": "Hello",
        "smtp_password": "super-secret-password",
        "imap_password": "super-secret-password",
    }
    resp = client.post("/api/v1/mailboxes", json=payload, headers=auth_headers)
    assert resp.status_code == 400
    assert "MAILCOW_SMTP_HOST" in resp.json()["detail"]
