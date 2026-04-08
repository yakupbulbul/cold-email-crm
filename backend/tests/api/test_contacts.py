from unittest.mock import patch

from fastapi.testclient import TestClient

from app.models.monitoring import JobLog
from app.models.lists import LeadList, LeadListMember
from app.models.verification import EmailVerificationLog


def test_list_contacts_supports_both_root_paths(client: TestClient, auth_headers: dict):
    resp_without_slash = client.get("/api/v1/leads", headers=auth_headers)
    resp_with_slash = client.get("/api/v1/leads/", headers=auth_headers)
    assert resp_without_slash.status_code == 200
    assert resp_with_slash.status_code == 200


def test_list_contacts_includes_persisted_list_membership(client: TestClient, auth_headers: dict, db, contact_factory):
    lead = contact_factory(email="person@example.com")
    lead_list = LeadList(name="Verified High Score", description="Reusable list", type="static")
    db.add(lead_list)
    db.commit()
    db.refresh(lead_list)

    db.add(LeadListMember(list_id=lead_list.id, lead_id=lead.id))
    db.commit()

    resp = client.get("/api/v1/leads", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    row = next(item for item in payload if item["id"] == str(lead.id))
    assert row["list_ids"] == [str(lead_list.id)]
    assert row["list_names"] == ["Verified High Score"]


def test_list_contacts_includes_b2b_b2c_fields_and_filters(client: TestClient, auth_headers: dict, db, contact_factory):
    b2b = contact_factory(
        email="b2b@example.com",
        contact_type="b2b",
        consent_status="unknown",
        unsubscribe_status="subscribed",
        engagement_score=55,
        tags=["saas", "founder"],
        industry="SaaS",
        persona="Founder",
    )
    contact_factory(
        email="b2c@example.com",
        contact_type="b2c",
        consent_status="granted",
        unsubscribe_status="subscribed",
        engagement_score=75,
        tags=["newsletter"],
    )

    resp = client.get("/api/v1/leads?contact_type=b2b&tag=saas&min_engagement_score=50", headers=auth_headers)
    assert resp.status_code == 200
    payload = resp.json()
    assert len(payload) == 1
    row = payload[0]
    assert row["id"] == str(b2b.id)
    assert row["contact_type"] == "b2b"
    assert row["consent_status"] == "unknown"
    assert row["unsubscribe_status"] == "subscribed"
    assert row["engagement_score"] == 55
    assert row["industry"] == "SaaS"
    assert row["persona"] == "Founder"
    assert row["tags"] == ["saas", "founder"]
    assert row["contact_quality_tier"] in {"high", "medium", "low"}


def test_single_lead_verification_persists_real_status(client: TestClient, auth_headers: dict, db, contact_factory):
    lead = contact_factory(email="person@example.com")

    with patch("app.services.verification_service.dns.resolver.resolve", return_value=[object()]):
        resp = client.post("/api/v1/leads/verify", headers=auth_headers, json={"lead_id": str(lead.id)})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["lead_id"] == str(lead.id)
    assert payload["status"] == "valid"
    assert payload["score"] == 100
    assert payload["integrity"] == "high"

    db.refresh(lead)
    assert lead.email_status == "valid"
    assert lead.verification_score == 100
    assert lead.verification_integrity == "high"
    assert lead.last_verified_at is not None

    logs = db.query(EmailVerificationLog).filter(EmailVerificationLog.contact_id == lead.id).all()
    assert len(logs) == 1
    assert logs[0].final_status == "valid"


def test_single_lead_verification_handles_duplicate_and_suppressed(client: TestClient, auth_headers: dict, db, contact_factory, suppression_factory):
    lead = contact_factory(email="shared@example.com")
    contact_factory(email="SHARED@example.com")
    suppression_factory(email="shared@example.com")

    with patch("app.services.verification_service.dns.resolver.resolve", return_value=[object()]):
        resp = client.post("/api/v1/leads/verify", headers=auth_headers, json={"lead_id": str(lead.id)})

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "suppressed"
    assert payload["is_duplicate"] is True
    assert payload["is_suppressed"] is True
    assert payload["integrity"] == "low"
    assert any("suppression" in reason.lower() for reason in payload["reasons"])


def test_bulk_verification_runs_inline_in_lean_mode(client: TestClient, auth_headers: dict, db, contact_factory, monkeypatch):
    lead_one = contact_factory(email="one@example.com")
    lead_two = contact_factory(email="two@example.com")
    monkeypatch.setattr("app.api.v1.routes.leads.settings.BACKGROUND_WORKERS_ENABLED", False)

    with patch("app.services.verification_service.dns.resolver.resolve", return_value=[object()]):
        create_resp = client.post(
            "/api/v1/leads/verify/bulk",
            headers=auth_headers,
            json={"lead_ids": [str(lead_one.id), str(lead_two.id)]},
        )

    assert create_resp.status_code == 200
    create_payload = create_resp.json()
    assert create_payload["status"] == "completed"
    assert create_payload["worker_mode"] == "lean"

    job_resp = client.get(f"/api/v1/leads/verify/{create_payload['job_id']}", headers=auth_headers)
    assert job_resp.status_code == 200
    job_payload = job_resp.json()
    assert job_payload["status"] == "completed"
    assert job_payload["processed_count"] == 2
    assert len(job_payload["results"]) == 2

    job = db.query(JobLog).filter(JobLog.job_id == create_payload["job_id"]).first()
    assert job is not None
    assert job.status == "completed"


def test_verification_classifies_common_failure_modes(client: TestClient, auth_headers: dict, contact_factory):
    invalid_lead = contact_factory(email="not-an-email")
    disposable_lead = contact_factory(email="burner@mailinator.com")
    role_lead = contact_factory(email="support@example.com")
    no_mx_lead = contact_factory(email="user@no-mx.example")

    invalid_resp = client.post("/api/v1/leads/verify", headers=auth_headers, json={"lead_id": str(invalid_lead.id)})
    assert invalid_resp.status_code == 200
    assert invalid_resp.json()["status"] == "invalid"

    disposable_resp = client.post("/api/v1/leads/verify", headers=auth_headers, json={"lead_id": str(disposable_lead.id)})
    assert disposable_resp.status_code == 200
    assert disposable_resp.json()["status"] == "disposable"

    with patch("app.services.verification_service.dns.resolver.resolve", return_value=[object()]):
        role_resp = client.post("/api/v1/leads/verify", headers=auth_headers, json={"lead_id": str(role_lead.id)})
    assert role_resp.status_code == 200
    assert role_resp.json()["status"] == "role_based"

    with patch("app.services.verification_service.dns.resolver.resolve", side_effect=Exception("no mx")):
        no_mx_resp = client.post("/api/v1/leads/verify", headers=auth_headers, json={"lead_id": str(no_mx_lead.id)})
    assert no_mx_resp.status_code == 200
    assert no_mx_resp.json()["status"] == "no_mx"


def test_bulk_tagging_and_suppression_actions(client: TestClient, auth_headers: dict, db, contact_factory):
    lead_one = contact_factory(email="bulk-one@example.com")
    lead_two = contact_factory(email="bulk-two@example.com")

    tag_resp = client.patch(
        "/api/v1/leads/bulk/tags",
        headers=auth_headers,
        json={"lead_ids": [str(lead_one.id), str(lead_two.id)], "tags": ["vip", "newsletter"]},
    )
    assert tag_resp.status_code == 200
    db.refresh(lead_one)
    db.refresh(lead_two)
    assert lead_one.tags == ["newsletter", "vip"] or lead_one.tags == ["vip", "newsletter"]
    assert lead_two.tags == ["newsletter", "vip"] or lead_two.tags == ["vip", "newsletter"]

    suppress_resp = client.post(
        "/api/v1/leads/bulk/suppress",
        headers=auth_headers,
        json={"lead_ids": [str(lead_one.id), str(lead_two.id)], "reason": "compliance"},
    )
    assert suppress_resp.status_code == 200
    db.refresh(lead_one)
    assert lead_one.is_suppressed is True
    assert lead_one.unsubscribe_status == "suppressed"
