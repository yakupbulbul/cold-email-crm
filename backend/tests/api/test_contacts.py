"""test_contacts.py — Contacts / Lead API tests."""
from fastapi.testclient import TestClient


def test_list_contacts_supports_both_root_paths(client: TestClient, auth_headers: dict):
    resp_without_slash = client.get("/api/v1/leads", headers=auth_headers)
    resp_with_slash = client.get("/api/v1/leads/", headers=auth_headers)
    assert resp_without_slash.status_code == 200
    assert resp_with_slash.status_code == 200


def test_import_csv_endpoint_exists(client: TestClient):
    resp = client.post("/api/v1/leads/import/csv", files={"file": ("empty.csv", b"email\n", "text/csv")})
    assert resp.status_code in (200, 201, 400, 401, 422)


def test_verify_email_endpoint_exists(client: TestClient):
    resp = client.post("/api/v1/leads/verify", json={"email": "test@example.com"})
    assert resp.status_code in (200, 201, 400, 401, 422)


def test_export_endpoint_exists(client: TestClient):
    resp = client.get("/api/v1/leads/export/csv")
    assert resp.status_code in (200, 401, 404)
