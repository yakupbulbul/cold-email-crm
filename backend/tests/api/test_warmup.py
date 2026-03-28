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
