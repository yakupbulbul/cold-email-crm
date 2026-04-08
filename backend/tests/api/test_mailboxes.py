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


def test_update_and_delete_mailbox(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_PORT", 587)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_PORT", 993)

    domain_resp = client.post("/api/v1/domains", json={"name": "mailbox-edit.example.com"}, headers=auth_headers)
    domain_id = domain_resp.json()["id"]

    create_payload = {
        "domain_id": domain_id,
        "email": "hello@mailbox-edit.example.com",
        "display_name": "Hello",
        "smtp_password": "super-secret-password",
        "imap_password": "super-secret-password",
    }
    create_resp = client.post("/api/v1/mailboxes", json=create_payload, headers=auth_headers)
    mailbox_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/api/v1/mailboxes/{mailbox_id}",
        json={"display_name": "Updated Name", "daily_send_limit": 120, "status": "paused"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["display_name"] == "Updated Name"
    assert updated["daily_send_limit"] == 120
    assert updated["status"] == "paused"

    delete_resp = client.delete(f"/api/v1/mailboxes/{mailbox_id}", headers=auth_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "deleted"

    get_resp = client.get(f"/api/v1/mailboxes/{mailbox_id}", headers=auth_headers)
    assert get_resp.status_code == 404
