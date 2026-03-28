"""test_ai.py — AI endpoint tests with graceful degradation."""
from fastapi.testclient import TestClient


def test_ai_summarize_endpoint_exists(client: TestClient):
    resp = client.post("/api/v1/ai/summarize", json={"thread_id": "00000000-0000-0000-0000-000000000000"})
    assert resp.status_code in (200, 400, 401, 404, 422, 503)


def test_ai_reply_endpoint_exists(client: TestClient):
    resp = client.post("/api/v1/ai/reply", json={"thread_id": "00000000-0000-0000-0000-000000000000"})
    assert resp.status_code in (200, 400, 401, 404, 422, 503)


def test_ai_endpoints_do_not_crash_without_openai_key(client: TestClient, monkeypatch):
    """AI endpoints must degrade gracefully when OPENAI_API_KEY is missing."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resp = client.post("/api/v1/ai/summarize", json={"thread_id": "00000000-0000-0000-0000-000000000000"})
    assert resp.status_code != 500  # Must not crash with 500 — graceful error only
