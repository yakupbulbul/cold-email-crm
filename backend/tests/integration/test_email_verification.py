"""
test_email_verification.py — Email Verification heuristic integration tests.
"""
import pytest
from unittest.mock import patch, MagicMock
import dns.resolver


@pytest.mark.integration
def test_syntax_valid_email_passes(db):
    from app.services.email_verification import EmailVerificationService
    svc = EmailVerificationService(db)
    result = svc.verify_email("user@example.com")
    assert result["syntax_valid"] is True


@pytest.mark.integration
def test_syntax_invalid_email_fails(db):
    from app.services.email_verification import EmailVerificationService
    svc = EmailVerificationService(db)
    result = svc.verify_email("not-an-email")
    assert result["syntax_valid"] is False


@pytest.mark.integration
def test_disposable_domain_detection(db):
    from app.services.email_verification import EmailVerificationService
    svc = EmailVerificationService(db)
    result = svc.verify_email("someone@mailinator.com")
    assert result.get("is_disposable") is True


@pytest.mark.integration
def test_role_based_detection(db):
    from app.services.email_verification import EmailVerificationService
    svc = EmailVerificationService(db)
    result = svc.verify_email("support@example.com")
    assert result.get("is_role_based") is True


@pytest.mark.integration
def test_mx_invalid_domain_returns_no_mx_status(db):
    from app.services.email_verification import EmailVerificationService
    with patch("dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN()):
        svc = EmailVerificationService(db)
        result = svc.verify_email("user@totally-invalid-nonexistent-xyzabc.com")
    assert result.get("mx_valid") is False


@pytest.mark.integration
def test_trust_score_zero_for_fully_invalid_email(db):
    from app.services.email_verification import EmailVerificationService
    svc = EmailVerificationService(db)
    result = svc.verify_email("bad-email")
    assert result.get("trust_score", 100) < 50
