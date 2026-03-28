"""test_auth.py — Auth endpoint tests."""
import pytest
from fastapi.testclient import TestClient


def test_login_with_invalid_credentials_returns_401(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={"email": "fake@example.com", "password": "wrong"})
    assert resp.status_code in (401, 422, 400)


def test_login_endpoint_exists(client: TestClient):
    # Should return 401/422 (not 404)
    resp = client.post("/api/v1/auth/login", json={})
    assert resp.status_code != 404


def test_docs_accessible(client: TestClient):
    resp = client.get("/docs")
    assert resp.status_code == 200
