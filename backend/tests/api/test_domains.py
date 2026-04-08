"""test_domains.py — Domain API endpoint tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.integrations.mailcow.client import MailcowDomainLookup


class FakeDNSRecord:
    def __init__(self, value: str):
        self.value = value

    def __str__(self) -> str:
        return self.value

    def to_text(self) -> str:
        return self.value


def _mailcow_verified(*args, **kwargs) -> MailcowDomainLookup:
    return MailcowDomainLookup(
        status="verified",
        detail="Domain found in remote Mailcow.",
        exists=True,
        http_status=200,
    )


def _mailcow_missing(*args, **kwargs) -> MailcowDomainLookup:
    return MailcowDomainLookup(
        status="not_found",
        detail="Domain not found in remote Mailcow.",
        exists=False,
        http_status=404,
    )


def test_list_domains_returns_200(client: TestClient, auth_headers: dict):
    resp = client.get("/api/v1/domains", headers=auth_headers)
    assert resp.status_code == 200


def test_create_domain_with_valid_data(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.integrations.mailcow.client.MailcowClient.lookup_domain", _mailcow_missing)
    resp = client.post("/api/v1/domains", json={
        "name": "test-domain.com",
    }, headers=auth_headers)
    assert resp.status_code in (200, 201)
    payload = resp.json()
    assert payload["status"] == "local_only"
    assert payload["mailcow_status"] == "missing"
    assert "missing_requirements" in payload


def test_create_domain_invalid_name_rejected(client: TestClient, auth_headers: dict):
    resp = client.post("/api/v1/domains", json={"name": ""}, headers=auth_headers)
    assert resp.status_code in (400, 422)


def test_verify_domain_reports_ready_when_mailcow_and_dns_pass(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.integrations.mailcow.client.MailcowClient.lookup_domain", _mailcow_verified)

    def fake_resolve(name: str, record_type: str):
        if record_type == "MX":
            return [FakeDNSRecord("10 mail.example.com.")]
        if name.startswith("_dmarc."):
            return [FakeDNSRecord("v=DMARC1; p=none")]
        if name.startswith("dkim._domainkey."):
            return [FakeDNSRecord("v=DKIM1; k=rsa; p=test")]
        return [FakeDNSRecord("v=spf1 include:_spf.example.com ~all")]

    monkeypatch.setattr("dns.resolver.resolve", fake_resolve)

    create_resp = client.post("/api/v1/domains", json={"name": "ready-domain.com"}, headers=auth_headers)
    assert create_resp.status_code == 200
    domain_id = create_resp.json()["id"]

    verify_resp = client.post(f"/api/v1/domains/{domain_id}/verify", headers=auth_headers)
    assert verify_resp.status_code == 200
    payload = verify_resp.json()
    assert payload["status"] == "ready"
    assert payload["mailcow_status"] == "verified"
    assert payload["mx_status"] == "configured"
    assert payload["spf_status"] == "configured"
    assert payload["dkim_status"] == "configured"
    assert payload["dmarc_status"] == "configured"
    assert payload["missing_requirements"] == []


def test_domain_status_endpoint_returns_structured_summary(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.integrations.mailcow.client.MailcowClient.lookup_domain", _mailcow_missing)
    create_resp = client.post("/api/v1/domains", json={"name": "status-domain.com"}, headers=auth_headers)
    domain_id = create_resp.json()["id"]

    status_resp = client.get(f"/api/v1/domains/{domain_id}/status", headers=auth_headers)
    assert status_resp.status_code == 200
    payload = status_resp.json()
    assert payload["status"] == "local_only"
    assert payload["mailcow_status"] == "missing"
    assert isinstance(payload["missing_requirements"], list)
    assert set(payload["dns"].keys()) == {"mx", "spf", "dkim", "dmarc"}


def test_delete_domain_removes_local_record(client: TestClient, auth_headers: dict, monkeypatch):
    monkeypatch.setattr("app.integrations.mailcow.client.MailcowClient.lookup_domain", _mailcow_missing)
    create_resp = client.post("/api/v1/domains", json={"name": "delete-domain.com"}, headers=auth_headers)
    assert create_resp.status_code == 200
    domain_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/api/v1/domains/{domain_id}", headers=auth_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"status": "success", "id": domain_id}

    get_resp = client.get(f"/api/v1/domains/{domain_id}", headers=auth_headers)
    assert get_resp.status_code == 404
