"""
test_failure_injection.py — Failure injection and resilience tests.

Verifies that the ops dashboard and health endpoints reflect degraded/failed
states when core infrastructure is unavailable.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


@pytest.mark.integration
def test_health_reflects_redis_failure(client: TestClient):
    """When Redis is unreachable, health endpoint reports redis as failed."""
    with patch("redis.Redis.from_url", side_effect=Exception("Connection refused")):
        resp = client.get("/api/v1/ops/health/redis")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("failed", "degraded", "unknown")


@pytest.mark.integration
def test_health_reflects_db_failure(client: TestClient):
    """When DB query fails, health/db reports failed."""
    with patch("sqlalchemy.orm.Session.execute", side_effect=Exception("DB Down")):
        resp = client.get("/api/v1/ops/health/db")
    # May still return 200 with failed status inside body
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        assert resp.json().get("status") in ("failed", "degraded", "unknown")


@pytest.mark.integration
def test_smtp_health_reflects_connection_failure(client: TestClient):
    """SMTP health check returns failed when host is unreachable."""
    resp = client.get("/api/v1/ops/health/smtp?host=invalid.host.test&port=465")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("failed", "unknown")


@pytest.mark.integration
def test_imap_health_reflects_connection_failure(client: TestClient):
    """IMAP health check returns failed when host is unreachable."""
    resp = client.get("/api/v1/ops/health/imap?host=invalid.host.test&port=993")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("failed", "unknown")


@pytest.mark.integration
def test_readiness_degrades_when_redis_unavailable(client: TestClient):
    """Readiness checklist shows degraded/failed when Redis is down."""
    with patch("redis.Redis.from_url", side_effect=Exception("Redis unavailable")):
        resp = client.get("/api/v1/ops/readiness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("failed", "degraded")
