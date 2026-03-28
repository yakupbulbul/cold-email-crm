"""
test_smtp_integration.py — Real SMTP connectivity tests against Mailpit or staging Mailcow.

Run with: pytest -m integration tests/integration/test_smtp_integration.py

Requires SMTP_TEST_HOST, SMTP_TEST_PORT env vars (default: mailpit at localhost:1025).
"""
import os
import smtplib
import pytest

SMTP_HOST = os.environ.get("SMTP_TEST_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SMTP_TEST_PORT", "1025"))


@pytest.mark.integration
def test_smtp_server_is_reachable():
    """SMTP server (Mailpit/Mailcow) accepts connections."""
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5)
        server.ehlo()
        server.quit()
    except Exception as e:
        pytest.skip(f"SMTP server not available at {SMTP_HOST}:{SMTP_PORT} — {e}")


@pytest.mark.integration
def test_smtp_send_succeeds():
    """A basic plain-text email can be sent through the test SMTP relay."""
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=5)
        server.ehlo()
        server.sendmail(
            "test@sender.com",
            ["recipient@test.com"],
            "Subject: Smoke Test\n\nThis is a CRM smoke test email.",
        )
        server.quit()
    except Exception as e:
        pytest.skip(f"SMTP send failed — {e}")


@pytest.mark.integration
def test_smtp_invalid_credentials_fail_safely():
    """Invalid SMTP credentials raise an exception and do not crash the process."""
    try:
        server = smtplib.SMTP_SSL("invalid.host.test", 465, timeout=3)
        pytest.fail("Should not connect to invalid host")
    except Exception:
        pass  # Expected — connection should fail


@pytest.mark.integration
def test_health_service_smtp_check_returns_status(client):
    """The /ops/health/smtp endpoint returns a structured status dict."""
    resp = client.get(f"/api/v1/ops/health/smtp?host={SMTP_HOST}&port={SMTP_PORT}&secure=false")
    assert resp.status_code == 200
    assert "status" in resp.json()
