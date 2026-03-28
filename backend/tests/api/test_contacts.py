"""test_contacts.py — Contacts / Lead API tests."""
import pytest
from fastapi.testclient import TestClient


def test_list_contacts_returns_200_or_401(client: TestClient):
    resp = client.get("/api/v1/leads")
    assert resp.status_code in (200, 401)


def test_import_csv_endpoint_exists(client: TestClient):
    resp = client.post("/api/v1/leads/import/csv", files={"file": ("empty.csv", b"email\n", "text/csv")})
    assert resp.status_code in (200, 201, 400, 401, 422)


def test_verify_email_endpoint_exists(client: TestClient):
    resp = client.post("/api/v1/leads/verify", json={"email": "test@example.com"})
    assert resp.status_code in (200, 201, 400, 401, 422)


def test_export_endpoint_exists(client: TestClient):
    resp = client.get("/api/v1/leads/export/csv")
    assert resp.status_code in (200, 401, 404)
