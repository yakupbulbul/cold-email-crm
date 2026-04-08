"""test_imports.py — Lead import endpoint tests."""
from fastapi.testclient import TestClient
from app.models.campaign import Contact


def test_upload_csv_creates_import_job(client: TestClient, auth_headers: dict):
    csv_content = b"email,first_name,last_name,company\nlead@example.com,Ada,Lovelace,Analytical Engines\n"

    response = client.post(
        "/api/v1/leads/import/csv",
        headers=auth_headers,
        files={"file": ("leads.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "parsed"
    assert payload["total_rows_parsed"] == 1
    assert payload["job_id"]


def test_confirm_import_persists_import_job_reference(client: TestClient, auth_headers: dict, db):
    csv_content = b"email,first_name,last_name,company\nlead@example.com,Ada,Lovelace,Analytical Engines\n"

    upload_response = client.post(
        "/api/v1/leads/import/csv",
        headers=auth_headers,
        files={"file": ("leads.csv", csv_content, "text/csv")},
    )
    job_id = upload_response.json()["job_id"]

    map_response = client.post(
        f"/api/v1/leads/import/{job_id}/map",
        headers=auth_headers,
        json={"field_mappings": {"email": "email", "first_name": "first_name", "last_name": "last_name", "company": "company"}},
    )
    assert map_response.status_code == 200

    confirm_response = client.post(f"/api/v1/leads/import/{job_id}/confirm", headers=auth_headers)
    assert confirm_response.status_code == 200

    contact = db.query(Contact).filter(Contact.email == "lead@example.com").first()
    assert contact is not None
    assert str(contact.source_import_job_id) == job_id
    assert contact.source_file_name == "leads.csv"
    assert contact.email_status == "unverified"
