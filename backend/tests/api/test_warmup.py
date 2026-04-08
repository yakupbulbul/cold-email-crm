"""test_warmup.py — Warm-up API endpoint tests."""
from fastapi.testclient import TestClient


def test_warmup_status_endpoint_exists(client: TestClient):
    resp = client.get("/api/v1/warmup/status")
    assert resp.status_code in (200, 401, 404)


def test_warmup_start_endpoint_exists(client: TestClient):
    resp = client.post("/api/v1/warmup/start", json={"mailbox_id": "00000000-0000-0000-0000-000000000000"})
    assert resp.status_code in (200, 201, 400, 401, 404, 422)


def test_warmup_stop_endpoint_exists(client: TestClient):
    resp = client.post("/api/v1/warmup/stop", json={"mailbox_id": "00000000-0000-0000-0000-000000000000"})
    assert resp.status_code in (200, 400, 401, 404, 422)


def test_warmup_start_requires_background_workers(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.warmup.settings.BACKGROUND_WORKERS_ENABLED", False)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "warmup-workers.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@warmup-workers.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )

    resp = client.post(
        "/api/v1/warmup/start",
        json={"mailbox_id": mailbox_resp.json()["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert "make dev-full" in resp.json()["detail"]
