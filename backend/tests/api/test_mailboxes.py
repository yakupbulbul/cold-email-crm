"""test_mailboxes.py — Mailbox endpoint coverage for host defaults and safe responses."""
from fastapi.testclient import TestClient
from app.models.core import Mailbox
from app.services.google_oauth_service import GoogleOAuthError


def _mailbox_payload(domain_id: str, email: str) -> dict:
    return {
        "domain_id": domain_id,
        "email": email,
        "display_name": "Hello",
        "smtp_password": "super-secret-password",
        "imap_password": "super-secret-password",
    }


def test_create_mailbox_uses_server_side_defaults(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_PORT", 587)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_PORT", 993)

    domain_resp = client.post("/api/v1/domains", json={"name": "mailbox-test.example.com"}, headers=auth_headers)
    domain_id = domain_resp.json()["id"]

    payload = _mailbox_payload(domain_id, "hello@mailbox-test.example.com")
    resp = client.post("/api/v1/mailboxes", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["smtp_host"] == "smtp.example.com"
    assert body["imap_host"] == "imap.example.com"
    assert "smtp_password" not in body
    assert "imap_password" not in body
    assert "smtp_password_encrypted" not in body
    assert "imap_password_encrypted" not in body
    assert body["remote_mailcow_provisioned"] is False
    assert body["provisioning_mode"] == "local_only"
    assert body["smtp_security_mode"] == "starttls"
    assert body["smtp_last_checked_at"] is None


def test_create_mailbox_requires_hosts_without_server_defaults(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", None)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", None)

    domain_resp = client.post("/api/v1/domains", json={"name": "manual-hosts.example.com"}, headers=auth_headers)
    domain_id = domain_resp.json()["id"]

    payload = _mailbox_payload(domain_id, "hello@manual-hosts.example.com")
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

    create_payload = _mailbox_payload(domain_id, "hello@mailbox-edit.example.com")
    create_resp = client.post("/api/v1/mailboxes", json=create_payload, headers=auth_headers)
    mailbox_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/api/v1/mailboxes/{mailbox_id}",
        json={"display_name": "Updated Name", "daily_send_limit": 120, "status": "paused", "smtp_security_mode": "ssl"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["display_name"] == "Updated Name"
    assert updated["daily_send_limit"] == 120
    assert updated["status"] == "paused"
    assert updated["smtp_security_mode"] == "ssl"

    delete_resp = client.delete(f"/api/v1/mailboxes/{mailbox_id}", headers=auth_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json()["status"] == "deleted"

    get_resp = client.get(f"/api/v1/mailboxes/{mailbox_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_create_mailbox_provisions_mailcow_when_mutations_enabled(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_PORT", 587)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_PORT", 993)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_ENABLE_MUTATIONS", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_API_URL", "https://mail.example.com/api/v1")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_API_KEY", "test-key")
    monkeypatch.setattr("app.integrations.mailcow.client.settings.MAILCOW_ENABLE_MUTATIONS", True)
    monkeypatch.setattr("app.integrations.mailcow.client.settings.MAILCOW_API_URL", "https://mail.example.com/api/v1")
    monkeypatch.setattr("app.integrations.mailcow.client.settings.MAILCOW_API_KEY", "test-key")

    domain_resp = client.post("/api/v1/domains", json={"name": "mailbox-sync.example.com"}, headers=auth_headers)
    domain_id = domain_resp.json()["id"]

    monkeypatch.setattr(
        "app.api.v1.routes.mailboxes.MailcowClient.lookup_domain",
        lambda self, domain_name: type("Lookup", (), {"status": "verified"})(),
    )
    monkeypatch.setattr(
        "app.api.v1.routes.mailboxes.MailcowClient.create_mailbox",
        lambda self, **kwargs: type("Provision", (), {"created": True, "reason": "created"})(),
    )

    resp = client.post(
        "/api/v1/mailboxes",
        json=_mailbox_payload(domain_id, "hello@mailbox-sync.example.com"),
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["remote_mailcow_provisioned"] is True
    assert body["provisioning_mode"] == "mailcow_synced"


def test_mailcow_provision_failure_keeps_no_local_mailbox(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_ENABLE_MUTATIONS", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_API_URL", "https://mail.example.com/api/v1")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_API_KEY", "test-key")

    domain_resp = client.post("/api/v1/domains", json={"name": "mailbox-fail.example.com"}, headers=auth_headers)
    domain_id = domain_resp.json()["id"]
    email = "hello@mailbox-fail.example.com"

    monkeypatch.setattr(
        "app.api.v1.routes.mailboxes.MailcowClient.lookup_domain",
        lambda self, domain_name: type("Lookup", (), {"status": "verified"})(),
    )
    monkeypatch.setattr(
        "app.api.v1.routes.mailboxes.MailcowClient.create_mailbox",
        lambda self, **kwargs: type("Provision", (), {"created": False, "reason": "mailbox_exists"})(),
    )

    resp = client.post("/api/v1/mailboxes", json=_mailbox_payload(domain_id, email), headers=auth_headers)
    assert resp.status_code == 409
    assert "remote Mailcow" in resp.json()["detail"]

    mailbox = db.query(Mailbox).filter(Mailbox.email == email).first()
    assert mailbox is None


def test_smtp_check_returns_structured_diagnostics(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    domain_resp = client.post("/api/v1/domains", json={"name": "smtp-check.example.com"}, headers=auth_headers)
    create_resp = client.post(
        "/api/v1/mailboxes",
        json=_mailbox_payload(domain_resp.json()["id"], "hello@smtp-check.example.com"),
        headers=auth_headers,
    )
    mailbox_id = create_resp.json()["id"]

    monkeypatch.setattr(
        "app.services.smtp_service.MailcowSMTPProvider.diagnose_connection",
        lambda self, **kwargs: type(
            "Diagnostic",
            (),
            {
                "status": "healthy",
                "category": "ok",
                "message": "SMTP host accepted the connection, negotiated the expected security mode, and authenticated successfully.",
                "host": kwargs["host"],
                "port": kwargs["port"],
                "security_mode": kwargs["security_mode"],
                "dns_resolved": True,
                "connected": True,
                "tls_negotiated": True,
                "auth_succeeded": True,
            },
        )(),
    )

    resp = client.post(f"/api/v1/mailboxes/{mailbox_id}/smtp-check", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "healthy"
    assert payload["category"] == "ok"
    assert payload["security_mode"] == "starttls"


def test_mailcow_unauthorized_failure_returns_safe_error(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_ENABLE_MUTATIONS", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_API_URL", "https://mail.example.com/api/v1")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_API_KEY", "test-key")

    domain_resp = client.post("/api/v1/domains", json={"name": "mailbox-auth.example.com"}, headers=auth_headers)
    domain_id = domain_resp.json()["id"]
    email = "hello@mailbox-auth.example.com"

    monkeypatch.setattr(
        "app.api.v1.routes.mailboxes.MailcowClient.lookup_domain",
        lambda self, domain_name: type("Lookup", (), {"status": "unauthorized"})(),
    )

    resp = client.post("/api/v1/mailboxes", json=_mailbox_payload(domain_id, email), headers=auth_headers)
    assert resp.status_code == 502
    assert resp.json()["detail"] == "Mailcow rejected the configured credentials."

    mailbox = db.query(Mailbox).filter(Mailbox.email == email).first()
    assert mailbox is None


def _google_mailbox_payload(domain_id: str, email: str) -> dict:
    return {
        "domain_id": domain_id,
        "email": email,
        "display_name": "Google Sender",
        "provider_type": "google_workspace",
        "oauth_enabled": True,
    }


def _enable_google_workspace_provider(client: TestClient, auth_headers: dict) -> None:
    resp = client.patch(
        "/api/v1/settings/providers",
        json={"google_workspace_enabled": True, "default_provider": "google_workspace"},
        headers=auth_headers,
    )
    assert resp.status_code == 200


def test_google_workspace_connect_endpoint_returns_authorization_url(client: TestClient, auth_headers: dict, monkeypatch):
    _enable_google_workspace_provider(client, auth_headers)
    domain_resp = client.post("/api/v1/domains", json={"name": "google-connect.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json=_google_mailbox_payload(domain_resp.json()["id"], "info@google-connect.example.com"),
        headers=auth_headers,
    )
    mailbox_id = mailbox_resp.json()["id"]

    monkeypatch.setattr(
        "app.api.v1.routes.mailboxes.GoogleWorkspaceOAuthService.build_authorization_url",
        lambda self, mailbox: "https://accounts.google.com/o/oauth2/v2/auth?state=test-state",
    )

    resp = client.post(f"/api/v1/mailboxes/{mailbox_id}/google-workspace/connect", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"
    assert "accounts.google.com" in resp.json()["authorization_url"]


def test_google_workspace_disconnect_endpoint_clears_oauth_state(client: TestClient, auth_headers: dict):
    _enable_google_workspace_provider(client, auth_headers)
    domain_resp = client.post("/api/v1/domains", json={"name": "google-disconnect.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json=_google_mailbox_payload(domain_resp.json()["id"], "info@google-disconnect.example.com"),
        headers=auth_headers,
    )
    mailbox_id = mailbox_resp.json()["id"]

    update_resp = client.put(
        f"/api/v1/mailboxes/{mailbox_id}",
        json={"display_name": "Google Sender", "daily_send_limit": 50, "status": "active", "provider_type": "google_workspace", "oauth_enabled": True},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200

    mailbox = client.get(f"/api/v1/mailboxes/{mailbox_id}", headers=auth_headers).json()
    assert mailbox["oauth_connection_status"] == "not_connected"

    disconnect_resp = client.post(f"/api/v1/mailboxes/{mailbox_id}/google-workspace/disconnect", headers=auth_headers)
    assert disconnect_resp.status_code == 200
    assert disconnect_resp.json()["oauth_connection_status"] == "not_connected"


def test_google_workspace_callback_redirects_back_to_mailboxes(client: TestClient, auth_headers: dict, monkeypatch):
    _enable_google_workspace_provider(client, auth_headers)
    domain_resp = client.post("/api/v1/domains", json={"name": "google-callback.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json=_google_mailbox_payload(domain_resp.json()["id"], "info@google-callback.example.com"),
        headers=auth_headers,
    )
    mailbox_id = mailbox_resp.json()["id"]

    monkeypatch.setattr(
        "app.api.v1.routes.auth.settings.ALLOWED_ORIGINS",
        ["http://localhost:3010"],
    )
    monkeypatch.setattr(
        "app.api.v1.routes.auth.GoogleWorkspaceOAuthService.decode_state",
        lambda self, state: {"mailbox_id": mailbox_id, "provider": "google_workspace"},
    )
    monkeypatch.setattr(
        "app.api.v1.routes.auth.GoogleWorkspaceOAuthService.exchange_code",
        lambda self, code, state: type("Token", (), {"mailbox_id": mailbox_id, "external_account_email": "info@google-callback.example.com"})(),
    )

    resp = client.get(
        "/api/v1/auth/google-workspace/callback",
        params={"code": "oauth-code", "state": "opaque-state"},
        headers=auth_headers,
        follow_redirects=False,
    )
    assert resp.status_code == 303
    location = resp.headers["location"]
    assert location.startswith("http://localhost:3010/mailboxes?")
    assert f"mailbox_id={mailbox_id}" in location
    assert "oauth_status=connected" in location


def test_google_workspace_callback_redirects_with_error_state(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.routes.auth.settings.ALLOWED_ORIGINS",
        ["http://localhost:3010"],
    )
    monkeypatch.setattr(
        "app.api.v1.routes.auth.GoogleWorkspaceOAuthService.decode_state",
        lambda self, state: {"mailbox_id": "mailbox-123", "provider": "google_workspace"},
    )

    def raise_exchange_error(self, code, state):
        raise GoogleOAuthError("Google denied the request.", category="oauth_exchange_failed", status_code=502)

    monkeypatch.setattr(
        "app.api.v1.routes.auth.GoogleWorkspaceOAuthService.exchange_code",
        raise_exchange_error,
    )

    resp = client.get(
        "/api/v1/auth/google-workspace/callback",
        params={"code": "oauth-code", "state": "opaque-state"},
        headers=auth_headers,
        follow_redirects=False,
    )
    assert resp.status_code == 303
    location = resp.headers["location"]
    assert location.startswith("http://localhost:3010/mailboxes?")
    assert "mailbox_id=mailbox-123" in location
    assert "oauth_status=oauth_exchange_failed" in location
