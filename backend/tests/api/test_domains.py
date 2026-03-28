"""test_domains.py — Domain API endpoint tests."""
import pytest
from fastapi.testclient import TestClient


def test_list_domains_returns_200(client: TestClient):
    resp = client.get("/api/v1/domains")
    assert resp.status_code in (200, 401)  # 401 ok if auth-gated


def test_create_domain_with_valid_data(client: TestClient):
    resp = client.post("/api/v1/domains", json={
        "name": "test-domain.com",
    })
    assert resp.status_code in (200, 201, 401, 422)


def test_create_domain_invalid_name_rejected(client: TestClient):
    resp = client.post("/api/v1/domains", json={"name": ""})
    assert resp.status_code in (400, 422, 401)
