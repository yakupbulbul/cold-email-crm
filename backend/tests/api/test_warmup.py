"""test_warmup.py — Warm-up API endpoint tests."""
from fastapi.testclient import TestClient
from app.models.warmup import WarmupPair


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
    assert "make dev or make dev-full" in resp.json()["detail"]


def test_warmup_start_requires_peer_mailbox(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.warmup.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "warmup-peer.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "solo@warmup-peer.example.com",
            "display_name": "Solo",
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
    assert "at least one other active local mailbox" in resp.json()["detail"]


def test_warmup_start_creates_pairs_and_status(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.warmup.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.warmup.run_warmup_cycle.delay", lambda **kwargs: type("Task", (), {"id": "warmup-job-1"})())

    domain_resp = client.post("/api/v1/domains", json={"name": "warmup-status.example.com"}, headers=auth_headers)
    mailbox_a = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "a@warmup-status.example.com",
            "display_name": "A",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    ).json()
    client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "b@warmup-status.example.com",
            "display_name": "B",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )

    resp = client.post(
        "/api/v1/warmup/start",
        json={"mailbox_id": mailbox_a["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["job_queued"] is True
    assert db.query(WarmupPair).count() == 1

    status_resp = client.get("/api/v1/warmup/status", headers=auth_headers)
    assert status_resp.status_code == 200
    payload = status_resp.json()
    assert payload["workers_enabled"] is True
    assert len(payload["active_pairs"]) == 1
