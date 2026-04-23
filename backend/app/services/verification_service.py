from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import dns.resolver
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.services.audience_service import evaluate_contact_for_campaign
from app.models.campaign import Contact
from app.models.suppression import SuppressionList
from app.models.verification import EmailVerificationLog


@dataclass
class BasicEmailCheckResult:
    normalized_email: str
    local_part: str
    domain: str
    syntax_valid: bool
    domain_valid: bool


@dataclass
class LeadVerificationResult:
    lead_id: str | None
    email: str
    status: str
    score: int
    integrity: str
    reasons: list[str]
    checked_at: str
    syntax_valid: bool
    domain_valid: bool
    mx_valid: bool
    is_disposable: bool
    is_role_based: bool
    is_duplicate: bool
    is_suppressed: bool


class BasicEmailCheckService:
    EMAIL_REGEX = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)

    def validate(self, email: str) -> BasicEmailCheckResult:
        normalized = email.strip().lower()
        if "@" not in normalized or not self.EMAIL_REGEX.match(normalized):
            return BasicEmailCheckResult(
                normalized_email=normalized,
                local_part="",
                domain="",
                syntax_valid=False,
                domain_valid=False,
            )

        local_part, domain = normalized.split("@", 1)
        domain_valid = bool(domain and "." in domain)
        return BasicEmailCheckResult(
            normalized_email=normalized,
            local_part=local_part,
            domain=domain,
            syntax_valid=True,
            domain_valid=domain_valid,
        )


class MXCheckService:
    def has_mx(self, domain: str) -> bool:
        try:
            answers = dns.resolver.resolve(domain, "MX")
            return len(answers) > 0
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, dns.exception.Timeout):
            return False
        except Exception:
            return False


class DisposableDomainService:
    DISPOSABLE_DOMAINS = {
        "10minutemail.com",
        "guerrillamail.com",
        "mailinator.com",
        "tempmail.com",
    }

    def is_disposable(self, domain: str) -> bool:
        return domain in self.DISPOSABLE_DOMAINS


class RoleBasedEmailService:
    ROLE_PREFIXES = {
        "admin",
        "billing",
        "contact",
        "hello",
        "info",
        "marketing",
        "sales",
        "support",
    }

    def is_role_based(self, local_part: str) -> bool:
        return local_part in self.ROLE_PREFIXES


class LeadScoringService:
    def calculate(self, *, syntax_valid: bool, domain_valid: bool, mx_valid: bool, is_disposable: bool, is_role_based: bool, is_duplicate: bool, is_suppressed: bool) -> tuple[int, str]:
        score = 0
        if syntax_valid:
            score += 20
        if domain_valid:
            score += 15
        if mx_valid:
            score += 20
        if not is_disposable:
            score += 10
        if not is_role_based:
            score += 10
        if not is_duplicate:
            score += 10
        if not is_suppressed:
            score += 15

        negative_flags = sum(1 for flag in (is_disposable, is_role_based, is_duplicate, is_suppressed) if flag)
        integrity = "low"
        if negative_flags > 0 or not syntax_valid or not domain_valid or not mx_valid:
            integrity = "low"
        elif syntax_valid and domain_valid and mx_valid and negative_flags == 0:
            integrity = "high"
        elif syntax_valid and domain_valid and mx_valid:
            integrity = "medium"
        return score, integrity


class EmailVerificationService:
    def __init__(self, db: Session):
        self.db = db
        self.basic_checks = BasicEmailCheckService()
        self.mx_checks = MXCheckService()
        self.disposable_domains = DisposableDomainService()
        self.role_based_emails = RoleBasedEmailService()
        self.scoring = LeadScoringService()

    def verify_lead(self, lead_id: str) -> LeadVerificationResult:
        contact = self.db.query(Contact).filter(Contact.id == lead_id).first()
        if not contact:
            raise ValueError("Lead not found")
        return self._verify_contact(contact)

    def verify_leads(self, lead_ids: list[str]) -> list[LeadVerificationResult]:
        contacts = self.db.query(Contact).filter(Contact.id.in_(lead_ids)).all()
        contact_map = {str(contact.id): contact for contact in contacts}
        missing = [lead_id for lead_id in lead_ids if lead_id not in contact_map]
        if missing:
            raise ValueError(f"Lead not found: {missing[0]}")
        return [self._verify_contact(contact_map[lead_id]) for lead_id in lead_ids]

    def _verify_contact(self, contact: Contact) -> LeadVerificationResult:
        checks = self.basic_checks.validate(contact.email)
        checked_at = datetime.now(timezone.utc)
        reasons: list[str] = []

        syntax_valid = checks.syntax_valid
        domain_valid = checks.domain_valid
        mx_valid = False
        is_disposable = False
        is_role_based = False
        is_suppressed = self._is_suppressed(checks.normalized_email)
        is_duplicate = self._is_duplicate(checks.normalized_email, str(contact.id))

        if not syntax_valid:
            reasons.append("Email syntax is invalid.")
        else:
            if not domain_valid:
                reasons.append("Email domain could not be parsed.")
            else:
                mx_valid = self.mx_checks.has_mx(checks.domain)
                if not mx_valid:
                    reasons.append("Domain does not have a valid MX record.")

                is_disposable = self.disposable_domains.is_disposable(checks.domain)
                if is_disposable:
                    reasons.append("Domain is disposable and unsafe for outreach.")

                is_role_based = self.role_based_emails.is_role_based(checks.local_part)
                if is_role_based:
                    reasons.append("Mailbox uses a role-based address.")

        if is_duplicate:
            reasons.append("Email already exists on another local lead.")
        if is_suppressed:
            reasons.append("Email is present in the suppression list.")

        score, integrity = self.scoring.calculate(
            syntax_valid=syntax_valid,
            domain_valid=domain_valid,
            mx_valid=mx_valid,
            is_disposable=is_disposable,
            is_role_based=is_role_based,
            is_duplicate=is_duplicate,
            is_suppressed=is_suppressed,
        )
        status = self._determine_status(
            syntax_valid=syntax_valid,
            mx_valid=mx_valid,
            score=score,
            is_disposable=is_disposable,
            is_role_based=is_role_based,
            is_duplicate=is_duplicate,
            is_suppressed=is_suppressed,
        )

        if status == "valid":
            reasons.append("Email passed syntax, MX, and local trust checks.")
        elif status == "risky" and not reasons:
            reasons.append("Email is usable but should be reviewed before outreach.")

        contact.email = checks.normalized_email
        contact.email_status = status
        contact.verification_score = score
        contact.verification_integrity = integrity
        contact.last_verified_at = checked_at
        contact.is_disposable = is_disposable
        contact.is_role_based = is_role_based
        contact.is_suppressed = is_suppressed
        contact.verification_reasons = reasons

        log = EmailVerificationLog(
            contact_id=contact.id,
            email=checks.normalized_email,
            syntax_valid=syntax_valid,
            domain_valid=domain_valid,
            mx_valid=mx_valid,
            disposable=is_disposable,
            role_based=is_role_based,
            duplicate=is_duplicate,
            suppressed=is_suppressed,
            verification_score=score,
            verification_integrity=integrity,
            verification_reasons=reasons,
            final_status=status,
            checked_at=checked_at,
        )
        self.db.add(contact)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(contact)
        self.db.refresh(log)

        return LeadVerificationResult(
            lead_id=str(contact.id),
            email=contact.email,
            status=status,
            score=score,
            integrity=integrity,
            reasons=reasons,
            checked_at=checked_at.isoformat(),
            syntax_valid=syntax_valid,
            domain_valid=domain_valid,
            mx_valid=mx_valid,
            is_disposable=is_disposable,
            is_role_based=is_role_based,
            is_duplicate=is_duplicate,
            is_suppressed=is_suppressed,
        )

    def _is_duplicate(self, email: str, lead_id: str) -> bool:
        duplicates = (
            self.db.query(func.count(Contact.id))
            .filter(func.lower(Contact.email) == email, Contact.id != lead_id)
            .scalar()
        )
        return bool(duplicates)

    def _is_suppressed(self, email: str) -> bool:
        return self.db.query(SuppressionList).filter(SuppressionList.email == email).first() is not None

    def _determine_status(
        self,
        *,
        syntax_valid: bool,
        mx_valid: bool,
        score: int,
        is_disposable: bool,
        is_role_based: bool,
        is_duplicate: bool,
        is_suppressed: bool,
    ) -> str:
        if is_suppressed:
            return "suppressed"
        if is_duplicate:
            return "duplicate"
        if is_disposable:
            return "disposable"
        if is_role_based:
            return "role_based"
        if not syntax_valid:
            return "invalid"
        if not mx_valid:
            return "no_mx"
        if score >= 90:
            return "valid"
        return "risky"


def verification_result_payload(result: LeadVerificationResult) -> dict:
    return asdict(result)


def contact_is_reachable(contact: Contact) -> bool:
    eligibility = evaluate_contact_for_campaign(contact)
    return eligibility.eligible
