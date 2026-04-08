from fastapi.testclient import TestClient

from app.models.campaign import CampaignLead, Contact


def test_list_crud_and_membership_persist(client: TestClient, auth_headers: dict, db):
    create_resp = client.post(
        "/api/v1/lists",
        json={"name": "April Outreach Batch", "description": "Reusable outreach list"},
        headers=auth_headers,
    )
    assert create_resp.status_code == 200
    lead_list = create_resp.json()
    assert lead_list["name"] == "April Outreach Batch"
    assert lead_list["lead_count"] == 0

    lead = Contact(email="list-member@example.com", first_name="List", email_status="valid", verification_score=95)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    add_resp = client.post(
        f"/api/v1/lists/{lead_list['id']}/leads",
        json={"lead_id": str(lead.id)},
        headers=auth_headers,
    )
    assert add_resp.status_code == 200
    assert add_resp.json()["lead_count"] == 1

    duplicate_resp = client.post(
        f"/api/v1/lists/{lead_list['id']}/leads",
        json={"lead_id": str(lead.id)},
        headers=auth_headers,
    )
    assert duplicate_resp.status_code == 200
    assert duplicate_resp.json()["lead_count"] == 1

    detail_resp = client.get(f"/api/v1/lists/{lead_list['id']}/leads", headers=auth_headers)
    assert detail_resp.status_code == 200
    assert len(detail_resp.json()["leads"]) == 1

    update_resp = client.patch(
        f"/api/v1/lists/{lead_list['id']}",
        json={"description": "Updated"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "Updated"

    remove_resp = client.delete(f"/api/v1/lists/{lead_list['id']}/leads/{lead.id}", headers=auth_headers)
    assert remove_resp.status_code == 200

    delete_resp = client.delete(f"/api/v1/lists/{lead_list['id']}", headers=auth_headers)
    assert delete_resp.status_code == 200


def test_bulk_membership_and_campaign_list_deduplication(client: TestClient, auth_headers: dict, monkeypatch, db):
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr("app.api.v1.routes.mailboxes.settings.MAILCOW_IMAP_HOST", "imap.example.com")

    domain_resp = client.post("/api/v1/domains", json={"name": "lists-campaign.example.com"}, headers=auth_headers)
    mailbox_resp = client.post(
        "/api/v1/mailboxes",
        json={
            "domain_id": domain_resp.json()["id"],
            "email": "sender@lists-campaign.example.com",
            "display_name": "Sender",
            "smtp_password": "super-secret-password",
            "imap_password": "super-secret-password",
        },
        headers=auth_headers,
    )
    campaign_resp = client.post(
        "/api/v1/campaigns",
        json={
            "name": "List Campaign",
            "mailbox_id": mailbox_resp.json()["id"],
            "template_subject": "Subject",
            "template_body": "Body",
            "daily_limit": 20,
        },
        headers=auth_headers,
    )

    lead_a = Contact(email="lead-a@example.com", first_name="A", email_status="valid", verification_score=95, verification_integrity="high")
    lead_b = Contact(email="lead-b@example.com", first_name="B", email_status="suppressed", verification_score=20, is_suppressed=True)
    lead_c = Contact(email="lead-c@example.com", first_name="C", email_status="risky", verification_score=75, verification_integrity="low")
    db.add_all([lead_a, lead_b, lead_c])
    db.commit()
    db.refresh(lead_a)
    db.refresh(lead_b)
    db.refresh(lead_c)

    list_one = client.post("/api/v1/lists", json={"name": "Batch One"}, headers=auth_headers).json()
    list_two = client.post("/api/v1/lists", json={"name": "Batch Two"}, headers=auth_headers).json()

    bulk_one = client.post(
        f"/api/v1/lists/{list_one['id']}/leads/bulk",
        json={"lead_ids": [str(lead_a.id), str(lead_b.id)]},
        headers=auth_headers,
    )
    assert bulk_one.status_code == 200
    bulk_two = client.post(
        f"/api/v1/lists/{list_two['id']}/leads/bulk",
        json={"lead_ids": [str(lead_a.id), str(lead_c.id)]},
        headers=auth_headers,
    )
    assert bulk_two.status_code == 200

    attach_one = client.post(
        f"/api/v1/campaigns/{campaign_resp.json()['id']}/lists",
        json={"list_id": list_one["id"]},
        headers=auth_headers,
    )
    assert attach_one.status_code == 200
    attach_two = client.post(
        f"/api/v1/campaigns/{campaign_resp.json()['id']}/lists",
        json={"list_id": list_two["id"]},
        headers=auth_headers,
    )
    assert attach_two.status_code == 200
    payload = attach_two.json()
    assert payload["lead_count"] == 3
    assert payload["reachable_count"] == 2
    assert payload["suppressed_count"] == 1
    assert len(payload["lists"]) == 2
    assert db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign_resp.json()["id"]).count() == 3

    list_resp = client.get(f"/api/v1/campaigns/{campaign_resp.json()['id']}/lists", headers=auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["lead_count"] == 3

    detach_resp = client.delete(
        f"/api/v1/campaigns/{campaign_resp.json()['id']}/lists/{list_one['id']}",
        headers=auth_headers,
    )
    assert detach_resp.status_code == 200
    assert detach_resp.json()["lead_count"] == 2
