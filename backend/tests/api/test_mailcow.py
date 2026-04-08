"""test_mailcow.py — Mailcow client tests with mocked network behavior."""
import httpx

from app.integrations.mailcow.client import MailcowClient


def test_mailcow_health_reports_unknown_when_not_configured(monkeypatch):
    monkeypatch.setattr("app.integrations.mailcow.client.settings.MAILCOW_API_URL", None)
    monkeypatch.setattr("app.integrations.mailcow.client.settings.MAILCOW_API_KEY", None)
    health = MailcowClient().check_health()
    assert health.status == "unknown"


def test_mailcow_health_reports_healthy_for_200(monkeypatch):
    monkeypatch.setattr("app.integrations.mailcow.client.settings.MAILCOW_API_URL", "https://mail.example.com/api/v1")
    monkeypatch.setattr("app.integrations.mailcow.client.settings.MAILCOW_API_KEY", "test-key")

    class Response:
        status_code = 200

    monkeypatch.setattr(MailcowClient, "_request", lambda self, method, path: Response())
    health = MailcowClient().check_health()
    assert health.status == "healthy"


def test_mailcow_health_reports_failed_when_unreachable(monkeypatch):
    monkeypatch.setattr("app.integrations.mailcow.client.settings.MAILCOW_API_URL", "https://mail.example.com/api/v1")
    monkeypatch.setattr("app.integrations.mailcow.client.settings.MAILCOW_API_KEY", "test-key")

    def raise_error(self, method, path):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(MailcowClient, "_request", raise_error)
    health = MailcowClient().check_health()
    assert health.status == "failed"
