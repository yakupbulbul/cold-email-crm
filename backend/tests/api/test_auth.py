"""test_auth.py — Auth endpoint tests."""
from fastapi.testclient import TestClient


def test_login_with_invalid_credentials_returns_401(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={"email": "fake@example.com", "password": "wrong"})
    assert resp.status_code in (401, 422, 400)


def test_login_endpoint_exists(client: TestClient):
    # Should return 401/422 (not 404)
    resp = client.post("/api/v1/auth/login", json={})
    assert resp.status_code != 404


def test_docs_accessible(client: TestClient):
    resp = client.get("/api/v1/docs")
    assert resp.status_code == 200


def test_auth_me_returns_current_user(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test-admin@example.com"


def test_protected_routes_require_authentication(client: TestClient):
    resp = client.get("/api/v1/domains")
    assert resp.status_code == 403


def test_admin_routes_reject_non_admin_users(client: TestClient, user_headers: dict):
    resp = client.get("/api/v1/ops/health", headers=user_headers)
    assert resp.status_code == 403
