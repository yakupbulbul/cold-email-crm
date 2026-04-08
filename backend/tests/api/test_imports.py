"""test_imports.py — Lead import endpoint tests."""
from fastapi.testclient import TestClient


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
