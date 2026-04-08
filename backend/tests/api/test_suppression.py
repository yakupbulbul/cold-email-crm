"""test_suppression.py — Suppression list API tests."""
import pytest
from fastapi.testclient import TestClient
import uuid


def test_list_suppression_returns_200_or_401(client: TestClient):
    resp = client.get("/api/v1/suppression")
    assert resp.status_code in (200, 401)


def test_add_suppression_valid_email(client: TestClient):
    resp = client.post("/api/v1/suppression", json={
        "email": f"suppress-{uuid.uuid4()}@test.com",
        "reason": "manual_test",
    })
    assert resp.status_code in (200, 201, 401, 422)


def test_add_suppression_invalid_email(client: TestClient):
    resp = client.post("/api/v1/suppression", json={"email": "not-an-email", "reason": "test"})
    assert resp.status_code in (400, 401, 422)


def test_delete_suppression_unknown_id(client: TestClient):
    resp = client.delete("/api/v1/suppression/00000000-0000-0000-0000-000000000000")
    assert resp.status_code in (200, 401, 404)


def test_list_suppression_trailing_slashless_route(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/suppression", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
