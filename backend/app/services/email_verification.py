from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.verification_service import (
    BasicEmailCheckService,
    DisposableDomainService,
    LeadScoringService,
    MXCheckService,
    RoleBasedEmailService,
)


class EmailVerificationService:
    """Compatibility wrapper for the older integration test contract."""

    def __init__(self, db: Session):
        self.db = db
        self.basic_checks = BasicEmailCheckService()
        self.mx_checks = MXCheckService()
        self.disposable_domains = DisposableDomainService()
        self.role_based_emails = RoleBasedEmailService()
        self.scoring = LeadScoringService()

    def verify_email(self, email: str) -> dict:
        checks = self.basic_checks.validate(email)

        syntax_valid = checks.syntax_valid
        domain_valid = checks.domain_valid
        mx_valid = self.mx_checks.has_mx(checks.domain) if syntax_valid and domain_valid else False
        is_disposable = self.disposable_domains.is_disposable(checks.domain) if checks.domain else False
        is_role_based = self.role_based_emails.is_role_based(checks.local_part) if checks.local_part else False

        trust_score, integrity = self.scoring.calculate(
            syntax_valid=syntax_valid,
            domain_valid=domain_valid,
            mx_valid=mx_valid,
            is_disposable=is_disposable,
            is_role_based=is_role_based,
            is_duplicate=False,
            is_suppressed=False,
        )

        return {
            "email": checks.normalized_email,
            "syntax_valid": syntax_valid,
            "domain_valid": domain_valid,
            "mx_valid": mx_valid,
            "is_disposable": is_disposable,
            "is_role_based": is_role_based,
            "trust_score": trust_score,
            "integrity": integrity,
        }
