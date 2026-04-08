from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.models.campaign import Campaign, Contact


STRICT_B2C_ALLOWED_CONSENT = {"granted", "not_required"}
REACHABLE_EMAIL_STATUSES = {"valid", "risky"}
BLOCKED_EMAIL_STATUSES = {"invalid", "no_mx", "disposable", "role_based", "duplicate", "suppressed"}


@dataclass
class AudienceEligibility:
    eligible: bool
    blocked_reason: str | None
    warning_reason: str | None = None


def normalize_tags(raw_tags: object) -> list[str]:
    if not raw_tags:
        return []
    if isinstance(raw_tags, list):
        return [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    if isinstance(raw_tags, str):
        return [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    return []


def quality_tier_for_contact(contact: Contact) -> str:
    if contact.is_suppressed or contact.unsubscribe_status in {"unsubscribed", "suppressed"}:
        return "low"
    if (contact.email_status or "unverified") == "valid" and (contact.verification_score or 0) >= 90 and (contact.engagement_score or 0) >= 40:
        return "high"
    if (contact.email_status or "unverified") in {"valid", "risky"} and (contact.verification_score or 0) >= 70:
        return "medium"
    return "low"


def campaign_allows_contact_type(contact: Contact, campaign_type: str | None) -> bool:
    if not campaign_type or not contact.contact_type:
        return True
    if campaign_type == "b2b":
        return contact.contact_type in {"b2b", "mixed"}
    if campaign_type == "b2c":
        return contact.contact_type in {"b2c", "mixed"}
    return True


def evaluate_contact_for_campaign(contact: Contact, campaign: Campaign | None = None) -> AudienceEligibility:
    email_status = contact.email_status or "unverified"
    campaign_type = campaign.campaign_type if campaign else None
    compliance_mode = campaign.compliance_mode if campaign else "standard"

    if contact.is_suppressed or email_status == "suppressed":
        return AudienceEligibility(eligible=False, blocked_reason="suppressed")
    if contact.unsubscribe_status in {"unsubscribed", "suppressed"}:
        return AudienceEligibility(eligible=False, blocked_reason="unsubscribed")
    if not campaign_allows_contact_type(contact, campaign_type):
        return AudienceEligibility(eligible=False, blocked_reason="type_mismatch")
    if email_status in BLOCKED_EMAIL_STATUSES or email_status == "unverified":
        return AudienceEligibility(eligible=False, blocked_reason=email_status)

    if campaign_type == "b2c":
        if compliance_mode == "strict_b2c" and contact.consent_status not in STRICT_B2C_ALLOWED_CONSENT:
            reason = "consent_unknown" if contact.consent_status == "unknown" else "consent_blocked"
            return AudienceEligibility(eligible=False, blocked_reason=reason)
        if email_status == "risky":
            if compliance_mode == "strict_b2c":
                return AudienceEligibility(eligible=False, blocked_reason="risky")
            return AudienceEligibility(eligible=True, blocked_reason=None, warning_reason="risky")

    if email_status == "risky":
        return AudienceEligibility(eligible=True, blocked_reason=None, warning_reason="risky")

    return AudienceEligibility(eligible=True, blocked_reason=None)


def summarize_contacts_for_campaign(contacts: list[Contact], campaign: Campaign | None = None) -> dict:
    deduped: dict[str, Contact] = {str(contact.id): contact for contact in contacts}
    items = list(deduped.values())

    status_counts = Counter((contact.email_status or "unverified") for contact in items)
    type_counts = Counter(contact.contact_type or "mixed" for contact in items)
    consent_counts = Counter(contact.consent_status or "unknown" for contact in items)
    unsubscribe_counts = Counter(contact.unsubscribe_status or "subscribed" for contact in items)
    quality_counts = Counter(quality_tier_for_contact(contact) for contact in items)
    industry_counts = Counter(contact.industry or "Unknown" for contact in items if contact.industry)
    persona_counts = Counter(contact.persona or "Unknown" for contact in items if contact.persona)

    reachable = 0
    risky = 0
    invalid = 0
    suppressed = 0
    unsubscribed = 0
    consent_unknown = 0
    type_mismatch = 0
    blocked_breakdown = Counter()

    for contact in items:
        eligibility = evaluate_contact_for_campaign(contact, campaign)
        email_status = contact.email_status or "unverified"
        if contact.is_suppressed or email_status == "suppressed":
            suppressed += 1
        if contact.unsubscribe_status in {"unsubscribed", "suppressed"}:
            unsubscribed += 1
        if contact.consent_status == "unknown":
            consent_unknown += 1
        if not campaign_allows_contact_type(contact, campaign.campaign_type if campaign else None):
            type_mismatch += 1

        if eligibility.eligible:
            reachable += 1
            if eligibility.warning_reason == "risky" or email_status == "risky":
                risky += 1
        else:
            invalid += 1
            blocked_breakdown[eligibility.blocked_reason or "unknown"] += 1

    return {
        "lead_count": len(items),
        "deduped_count": len(items),
        "reachable_count": reachable,
        "risky_count": risky,
        "invalid_count": invalid,
        "suppressed_count": suppressed,
        "unsubscribed_count": unsubscribed,
        "consent_unknown_count": consent_unknown,
        "type_mismatch_count": type_mismatch,
        "status_counts": dict(status_counts),
        "contact_type_counts": dict(type_counts),
        "consent_counts": dict(consent_counts),
        "unsubscribe_counts": dict(unsubscribe_counts),
        "quality_tier_counts": dict(quality_counts),
        "blocked_breakdown": dict(blocked_breakdown),
        "industry_counts": dict(industry_counts),
        "persona_counts": dict(persona_counts),
        "high_quality_count": quality_counts.get("high", 0),
        "medium_quality_count": quality_counts.get("medium", 0),
        "low_quality_count": quality_counts.get("low", 0),
    }
