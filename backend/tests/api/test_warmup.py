"""test_warmup.py — Warm-up operational API tests."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.models.core import Mailbox
from app.models.monitoring import JobLog, WorkerHeartbeat
from app.models.warmup import WarmupEvent, WarmupPair, WarmupSetting


def _create_mailbox(client: TestClient, auth_headers: dict, domain_id: str, email: str):
    return client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_id,
            "email": email,
            "display_name": email.split("@", 1)[0],
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    ).json()


def test_warmup_status_endpoint_exists(client: TestClient):
    resp = client.get("/api/v1/warmup/status")
    assert resp.status_code in (200, 401, 404)


def test_warmup_start_requires_background_workers(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.api.v1.routes.warmup.settings.BACKGROUND_WORKERS_ENABLED", False)
    resp = client.post("/api/v1/warmup/start", headers=auth_headers)
    assert resp.status_code == 409
    assert "make dev or make dev-full" in resp.json()["detail"]


def test_global_warmup_start_unpauses_without_auto_enabling_mailboxes(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.warmup.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "warmup-global.example.com"}, headers=auth_headers)
    _create_mailbox(client, auth_headers, domain_resp.json()["id"], "a@warmup-global.example.com")
    _create_mailbox(client, auth_headers, domain_resp.json()["id"], "b@warmup-global.example.com")

    resp = client.post("/api/v1/warmup/start", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "enabled"
    settings_row = db.query(WarmupSetting).first()
    assert settings_row is not None
    assert settings_row.is_enabled is True
    assert db.query(Mailbox).filter(Mailbox.warmup_enabled == True).count() == 0


def test_patch_mailbox_warmup_updates_participation_and_status(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "warmup-mailbox.example.com"}, headers=auth_headers)
    mailbox = _create_mailbox(client, auth_headers, domain_resp.json()["id"], "a@warmup-mailbox.example.com")
    mailbox_row = db.query(Mailbox).filter(Mailbox.id == mailbox["id"]).first()
    mailbox_row.smtp_last_check_status = "healthy"
    mailbox_row.smtp_last_check_message = "SMTP delivery succeeded."
    db.commit()

    resp = client.patch(
        f"/api/v1/mailboxes/{mailbox['id']}/warmup",
        json={"warmup_enabled": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["warmup_enabled"] is True
    assert payload["warmup_status"] == "ready"


def test_warmup_status_reports_blockers_and_mailbox_truth(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.warmup.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.services.warmup_service.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.services.health_service.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "warmup-status.example.com"}, headers=auth_headers)
    mailbox_a = _create_mailbox(client, auth_headers, domain_resp.json()["id"], "a@warmup-status.example.com")
    mailbox_b = _create_mailbox(client, auth_headers, domain_resp.json()["id"], "b@warmup-status.example.com")
    mailbox_a_row = db.query(Mailbox).filter(Mailbox.id == mailbox_a["id"]).first()
    mailbox_b_row = db.query(Mailbox).filter(Mailbox.id == mailbox_b["id"]).first()
    mailbox_a_row.warmup_enabled = True
    mailbox_b_row.warmup_enabled = True
    mailbox_a_row.smtp_last_check_status = "healthy"
    mailbox_b_row.smtp_last_check_status = "failed"
    mailbox_b_row.smtp_last_check_message = "SMTP timed out."
    db.add(
        WorkerHeartbeat(
            worker_name="dev-worker",
            worker_type="celery",
            status="healthy",
            last_seen_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    resp = client.get("/api/v1/warmup/status", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["global_status"] == "paused"
    assert payload["worker_status"]["status"] == "healthy"
    assert payload["scheduler_status"]["status"] in {"stale", "healthy"}
    assert payload["inboxes_warming_count"] == 2
    assert payload["next_run_at"] is None
    assert any(blocker["code"] == "warmup_paused" for blocker in payload["blockers"])
    assert any(blocker["code"] == "smtp_unhealthy" for blocker in payload["blockers"])
    assert len(payload["mailboxes"]) == 2


def test_warmup_pair_generation_is_bidirectional_for_ready_mailboxes(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.warmup.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.services.warmup_service.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.services.health_service.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.warmup.run_warmup_cycle.delay", lambda **kwargs: type("Task", (), {"id": "warmup-job-1"})())

    domain_resp = client.post("/api/v1/domains", json={"name": "warmup-pairs.example.com"}, headers=auth_headers)
    mailbox_a = _create_mailbox(client, auth_headers, domain_resp.json()["id"], "a@warmup-pairs.example.com")
    mailbox_b = _create_mailbox(client, auth_headers, domain_resp.json()["id"], "b@warmup-pairs.example.com")

    for mailbox in db.query(Mailbox).filter(Mailbox.id.in_([mailbox_a["id"], mailbox_b["id"]])).all():
        mailbox.warmup_enabled = True
        mailbox.smtp_last_check_status = "healthy"
        mailbox.smtp_last_check_message = "SMTP delivery succeeded."
    db.add(
        WorkerHeartbeat(
            worker_name="dev-worker",
            worker_type="celery",
            status="healthy",
            last_seen_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    start_resp = client.post("/api/v1/warmup/start", headers=auth_headers)
    assert start_resp.status_code == 200

    pairs_resp = client.get("/api/v1/warmup/pairs", headers=auth_headers)
    assert pairs_resp.status_code == 200
    payload = pairs_resp.json()
    assert len(payload) == 2
    assert {pair["sender_email"] for pair in payload} == {"a@warmup-pairs.example.com", "b@warmup-pairs.example.com"}
    assert db.query(WarmupPair).count() == 2


def test_warmup_logs_endpoint_returns_recent_activity(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "warmup-logs.example.com"}, headers=auth_headers)
    mailbox_a = _create_mailbox(client, auth_headers, domain_resp.json()["id"], "a@warmup-logs.example.com")
    mailbox_b = _create_mailbox(client, auth_headers, domain_resp.json()["id"], "b@warmup-logs.example.com")
    pair = WarmupPair(sender_mailbox_id=mailbox_a["id"], recipient_mailbox_id=mailbox_b["id"], is_active=True, state="active")
    db.add(pair)
    db.commit()
    db.refresh(pair)
    db.add(
        WarmupEvent(
            mailbox_id=mailbox_a["id"],
            pair_id=pair.id,
            recipient_mailbox_id=mailbox_b["id"],
            event_type="send",
            target_email="b@warmup-logs.example.com",
            status="failed",
            error_category="smtp_timeout",
            result_detail="SMTP timed out.",
        )
    )
    db.commit()

    resp = client.get("/api/v1/warmup/logs", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 1
    assert payload[0]["status"] == "failed"
    assert payload[0]["error_category"] == "smtp_timeout"


def test_warmup_pause_disables_active_pairs(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.warmup.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.services.warmup_service.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.services.health_service.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")
    monkeypatch.setattr("app.api.v1.routes.warmup.run_warmup_cycle.delay", lambda **kwargs: type("Task", (), {"id": "warmup-job-1"})())

    domain_resp = client.post("/api/v1/domains", json={"name": "warmup-pause.example.com"}, headers=auth_headers)
    mailbox_a = _create_mailbox(client, auth_headers, domain_resp.json()["id"], "a@warmup-pause.example.com")
    mailbox_b = _create_mailbox(client, auth_headers, domain_resp.json()["id"], "b@warmup-pause.example.com")
    for mailbox in db.query(Mailbox).filter(Mailbox.id.in_([mailbox_a["id"], mailbox_b["id"]])).all():
        mailbox.warmup_enabled = True
        mailbox.smtp_last_check_status = "healthy"
        mailbox.smtp_last_check_message = "SMTP delivery succeeded."
    db.add(
        WorkerHeartbeat(
            worker_name="dev-worker",
            worker_type="celery",
            status="healthy",
            last_seen_at=datetime.now(timezone.utc),
        )
    )
    db.commit()

    client.post("/api/v1/warmup/start", headers=auth_headers)
    pause_resp = client.post("/api/v1/warmup/pause", headers=auth_headers)
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"
    assert db.query(WarmupPair).filter(WarmupPair.is_active == True).count() == 0


def test_warmup_status_reports_recent_scheduler_truth(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.warmup.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.services.warmup_service.settings.BACKGROUND_WORKERS_ENABLED", True)
    monkeypatch.setattr("app.services.health_service.settings.BACKGROUND_WORKERS_ENABLED", True)

    db.add(
        WorkerHeartbeat(
            worker_name="dev-worker",
            worker_type="celery",
            status="healthy",
            last_seen_at=datetime.now(timezone.utc),
        )
    )
    db.add(
        JobLog(
            job_id="warmup-job-fresh",
            job_type="warmup_cycle",
            status="completed",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            finished_at=datetime.now(timezone.utc) - timedelta(minutes=4),
        )
    )
    db.commit()

    resp = client.get("/api/v1/warmup/status", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["scheduler_status"]["status"] == "healthy"
