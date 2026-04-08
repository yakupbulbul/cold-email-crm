"""test_domains.py — Domain API endpoint tests."""
from fastapi.testclient import TestClient


def test_list_domains_returns_200(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/domains", headers=auth_headers)
    assert resp.status_code == 200


def test_create_domain_with_valid_data(client: TestClient, auth_headers: dict):
    resp = client.post("/api/v1/domains", json={
        "name": "test-domain.com",
    }, headers=auth_headers)
    assert resp.status_code in (200, 201)


def test_create_domain_invalid_name_rejected(client: TestClient, auth_headers: dict):
    resp = client.post("/api/v1/domains", json={"name": ""}, headers=auth_headers)
    assert resp.status_code in (400, 422)
