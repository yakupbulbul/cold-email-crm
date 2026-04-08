"""test_ops.py — Ops/Telemetry endpoint tests."""
from fastapi.testclient import TestClient
from types import SimpleNamespace


def test_health_endpoint_returns_200(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/ops/health", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "components" in data


def test_health_db_endpoint(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/ops/health/db", headers=auth_headers)
    assert resp.status_code == 200
    assert "status" in resp.json()


def test_health_redis_endpoint(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/ops/health/redis", headers=auth_headers)
    assert resp.status_code == 200


def test_jobs_endpoint_exists(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/ops/jobs", headers=auth_headers)
    assert resp.status_code == 200


def test_alerts_endpoint_exists(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/ops/alerts", headers=auth_headers)
    assert resp.status_code == 200


def test_audit_logs_endpoint_exists(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/ops/audit-logs", headers=auth_headers)
    assert resp.status_code == 200


def test_readiness_endpoint_returns_structured_data(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/ops/readiness", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checklist" in data


def test_deliverability_summary_endpoint(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/ops/deliverability/summary", headers=auth_headers)
    assert resp.status_code == 200


def test_deliverability_mailboxes_endpoint(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/ops/deliverability/mailboxes", headers=auth_headers)
    assert resp.status_code == 200


def test_mailcow_health_endpoint_returns_safe_payload(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/ops/health/mailcow", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["service"] == "mailcow_api"
    assert "status" in payload
    assert "reason" in payload
    assert payload["mutations_enabled"] is False


def test_worker_health_reports_disabled_in_lean_mode(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/ops/health/workers", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["service"] == "workers"
    assert payload["status"] == "disabled"
    assert payload["enabled"] is False


def test_readiness_reports_disabled_workers_as_warning(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/ops/readiness", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    worker_check = next(item for item in payload["checklist"] if item["check"] == "Worker and Beat Processes")
    assert worker_check["status"] == "warning"


def test_worker_health_uses_live_celery_ping_when_enabled(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.services.health_service.settings.BACKGROUND_WORKERS_ENABLED", True)

    class FakeInspect:
        def ping(self):
            return {"celery@test-host": {"ok": "pong"}}

    monkeypatch.setattr(
        "app.workers.celery_app.celery_app.control",
        SimpleNamespace(inspect=lambda timeout=1: FakeInspect()),
    )

    resp = client.get("/api/v1/ops/health/workers", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "healthy"
    assert payload["enabled"] is True
    assert payload["active_count"] == 1
