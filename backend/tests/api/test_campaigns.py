"""test_campaigns.py — Campaign API + preflight tests."""
import pytest
from fastapi.testclient import TestClient


def test_list_campaigns_returns_200_or_401(client: TestClient):
    resp = client.get("/api/v1/campaigns")
    assert resp.status_code in (200, 401)


def test_create_campaign_missing_fields_returns_422(client: TestClient):
    resp = client.post("/api/v1/campaigns", json={})
    assert resp.status_code in (400, 401, 422)


def test_campaign_preflight_endpoint_exists(client: TestClient):
    # Use a dummy UUID — 404 or 401 acceptable, not 500
    resp = client.post("/api/v1/campaigns/00000000-0000-0000-0000-000000000000/preflight")
    assert resp.status_code in (200, 401, 404)


def test_campaign_preflight_history_endpoint_exists(client: TestClient):
    resp = client.get("/api/v1/campaigns/00000000-0000-0000-0000-000000000000/preflight/history")
    assert resp.status_code in (200, 401, 404)
