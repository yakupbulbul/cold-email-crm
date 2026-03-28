"""test_ops.py — Ops/Telemetry endpoint tests."""
import pytest
from fastapi.testclient import TestClient


def test_health_endpoint_returns_200(client: TestClient):
    resp = client.get("/api/v1/ops/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "components" in data


def test_health_db_endpoint(client: TestClient):
    resp = client.get("/api/v1/ops/health/db")
    assert resp.status_code == 200
    assert "status" in resp.json()


def test_health_redis_endpoint(client: TestClient):
    resp = client.get("/api/v1/ops/health/redis")
    assert resp.status_code == 200


def test_jobs_endpoint_exists(client: TestClient):
    resp = client.get("/api/v1/ops/jobs")
    assert resp.status_code in (200, 401)


def test_alerts_endpoint_exists(client: TestClient):
    resp = client.get("/api/v1/ops/alerts")
    assert resp.status_code in (200, 401)


def test_audit_logs_endpoint_exists(client: TestClient):
    resp = client.get("/api/v1/ops/audit-logs")
    assert resp.status_code in (200, 401)


def test_readiness_endpoint_returns_structured_data(client: TestClient):
    resp = client.get("/api/v1/ops/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "checklist" in data


def test_deliverability_summary_endpoint(client: TestClient):
    resp = client.get("/api/v1/ops/deliverability/summary")
    assert resp.status_code in (200, 401)


def test_deliverability_mailboxes_endpoint(client: TestClient):
    resp = client.get("/api/v1/ops/deliverability/mailboxes")
    assert resp.status_code in (200, 401)
