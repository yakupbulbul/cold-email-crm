from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.campaign import Campaign, CampaignLead, Contact, SendLog
from app.models.core import Domain, Mailbox
from app.models.monitoring import DeliverabilityEvent
from app.models.warmup import WarmupEvent, WarmupPair, WarmupSetting
from app.services.audience_service import evaluate_contact_for_campaign, summarize_contacts_for_campaign
from app.services.mail_provider_service import MailProviderRegistry, ProviderUnavailableError
from app.services.provider_settings_service import ProviderSettingsService


READINESS_ORDER = {
    "ready": 0,
    "warning": 1,
    "degraded": 2,
    "blocked": 3,
    "unknown": 1,
}


class DeliverabilityService:
    """Builds deliverability readiness from persisted operational truth.

    The service intentionally avoids live network checks. DNS, SMTP, IMAP, OAuth,
    provider, warm-up, send, and audience state are read from the same persisted
    diagnostics used elsewhere in the product.
    """

    def __init__(self, db: Session):
        self.db = db
        self.providers = MailProviderRegistry(db)

    def overview(self) -> dict[str, Any]:
        domains = self.domains()
        mailboxes = self.mailboxes()
        audience = self.audience_summary()
        warmup = self.warmup_summary()
        providers = self.provider_summary()
        campaigns = self.campaigns_summary()

        blockers = self._top_items(
            domains.get("blockers", [])
            + mailboxes.get("blockers", [])
            + providers.get("blockers", [])
            + warmup.get("blockers", [])
            + audience.get("blockers", [])
            + campaigns.get("blockers", [])
        )
        warnings = self._top_items(
            domains.get("warnings", [])
            + mailboxes.get("warnings", [])
            + providers.get("warnings", [])
            + warmup.get("warnings", [])
            + audience.get("warnings", [])
            + campaigns.get("warnings", []),
            limit=10,
        )
        status = self._combine_statuses(
            [
                domains["status"],
                mailboxes["status"],
                audience["status"],
                warmup["status"],
                providers["status"],
                campaigns["status"],
            ]
        )

        return {
            "status": status,
            "score": self._score_from_status(status),
            "generated_at": datetime.utcnow().isoformat(),
            "blockers": blockers,
            "warnings": warnings,
            "next_actions": self._next_actions(blockers, warnings),
            "summary": {
                "domains": domains["summary"],
                "mailboxes": mailboxes["summary"],
                "audience": audience["summary"],
                "warmup": warmup["summary"],
                "providers": providers["summary"],
                "campaigns": campaigns["summary"],
            },
            "domains": domains["items"],
            "mailboxes": mailboxes["items"],
            "audience": audience,
            "warmup": warmup,
            "providers": providers["items"],
            "campaigns": campaigns,
        }

    def domains(self) -> dict[str, Any]:
        items = [self.domain_readiness(domain) for domain in self.db.query(Domain).order_by(Domain.name.asc()).all()]
        return self._collection_payload(items, "domain_count")

    def domain_readiness(self, domain: Domain | str) -> dict[str, Any]:
        if isinstance(domain, str):
            domain = self.db.query(Domain).filter(Domain.id == domain).first()
        if not domain:
            return self._missing_entity("domain")

        checks = [
            self._domain_dns_check(domain, "mx", "MX record", blocker=True),
            self._domain_dns_check(domain, "spf", "SPF record", blocker=False),
            self._domain_dns_check(domain, "dkim", "DKIM record", blocker=False),
            self._domain_dns_check(domain, "dmarc", "DMARC record", blocker=False),
            self._domain_bimi_check(domain),
            self._domain_provider_check(domain),
        ]
        blockers, warnings = self._issues_from_checks(checks, source="domain", entity=str(domain.name))
        status = self._status_from_issues(blockers, warnings, checks)

        return {
            "id": str(domain.id),
            "type": "domain",
            "name": domain.name,
            "status": status,
            "score": self._score_from_checks(checks),
            "last_checked_at": self._iso(domain.dns_last_checked_at or domain.last_checked_at),
            "blockers": blockers,
            "warnings": warnings,
            "next_actions": self._next_actions(blockers, warnings),
            "checks": checks,
            "raw_status": domain.status,
        }

    def mailboxes(self) -> dict[str, Any]:
        items = [
            self.mailbox_readiness(mailbox)
            for mailbox in self.db.query(Mailbox).options(joinedload(Mailbox.domain), joinedload(Mailbox.oauth_token)).order_by(Mailbox.email.asc()).all()
        ]
        return self._collection_payload(items, "mailbox_count")

    def mailbox_readiness(self, mailbox: Mailbox | str) -> dict[str, Any]:
        if isinstance(mailbox, str):
            mailbox = self.db.query(Mailbox).options(joinedload(Mailbox.domain), joinedload(Mailbox.oauth_token)).filter(Mailbox.id == mailbox).first()
        if not mailbox:
            return self._missing_entity("mailbox")

        checks = [
            self._mailbox_status_check(mailbox),
            self._mailbox_provider_check(mailbox),
            self._mailbox_oauth_check(mailbox),
            self._mailbox_smtp_check(mailbox),
            self._mailbox_imap_check(mailbox),
            self._mailbox_warmup_check(mailbox),
            self._mailbox_recent_send_check(mailbox),
        ]
        if mailbox.domain:
            domain_status = self.domain_readiness(mailbox.domain)
            checks.append(
                {
                    "code": "domain_readiness",
                    "label": "Domain readiness",
                    "status": "pass" if domain_status["status"] == "ready" else "fail" if domain_status["status"] == "blocked" else "warning",
                    "severity": "critical" if domain_status["status"] == "blocked" else "warning" if domain_status["status"] != "ready" else "info",
                    "detail": f"{mailbox.domain.name} is {domain_status['status']}.",
                    "next_action": "Fix domain deliverability blockers before high-volume sending." if domain_status["status"] != "ready" else None,
                    "checked_at": domain_status["last_checked_at"],
                }
            )

        blockers, warnings = self._issues_from_checks(checks, source="mailbox", entity=mailbox.email)
        status = self._status_from_issues(blockers, warnings, checks)
        recent = self._recent_send_counts(mailbox.id)

        return {
            "id": str(mailbox.id),
            "type": "mailbox",
            "email": mailbox.email,
            "display_name": mailbox.display_name,
            "domain_id": str(mailbox.domain_id) if mailbox.domain_id else None,
            "domain": mailbox.domain.name if mailbox.domain else mailbox.email.split("@")[-1],
            "provider_type": mailbox.provider_type or "mailcow",
            "status": status,
            "score": self._score_from_checks(checks),
            "last_checked_at": self._iso(mailbox.smtp_last_checked_at or mailbox.last_provider_check_at or mailbox.warmup_last_checked_at),
            "blockers": blockers,
            "warnings": warnings,
            "next_actions": self._next_actions(blockers, warnings),
            "checks": checks,
            "recent_sends": recent,
            "warmup": {
                "enabled": bool(mailbox.warmup_enabled),
                "status": mailbox.warmup_status,
                "last_result": mailbox.warmup_last_result,
                "block_reason": mailbox.warmup_block_reason,
            },
        }

    def campaign_readiness(self, campaign_id: str) -> dict[str, Any]:
        campaign = self.db.query(Campaign).options(joinedload(Campaign.mailbox)).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return self._missing_entity("campaign")

        checks: list[dict[str, Any]] = []
        mailbox_payload = None
        if not campaign.mailbox:
            checks.append(self._check("mailbox_selected", "Mailbox selected", "fail", "critical", "Campaign has no sending mailbox.", "Select a healthy sending mailbox."))
        else:
            mailbox_payload = self.mailbox_readiness(campaign.mailbox)
            checks.append(
                self._check(
                    "mailbox_readiness",
                    "Mailbox readiness",
                    "pass" if mailbox_payload["status"] == "ready" else "fail" if mailbox_payload["status"] == "blocked" else "warning",
                    "critical" if mailbox_payload["status"] == "blocked" else "warning" if mailbox_payload["status"] != "ready" else "info",
                    f"{campaign.mailbox.email} is {mailbox_payload['status']}.",
                    "Resolve mailbox deliverability blockers before starting." if mailbox_payload["status"] == "blocked" else "Review mailbox warnings before sending." if mailbox_payload["status"] != "ready" else None,
                )
            )

        leads = self.db.query(CampaignLead).join(Contact).filter(CampaignLead.campaign_id == campaign.id).all()
        audience = summarize_contacts_for_campaign([lead.contact for lead in leads], campaign)
        eligible_count = 0
        blocked = Counter()
        for lead in leads:
            result = evaluate_contact_for_campaign(lead.contact, campaign)
            if lead.status == "scheduled" and result.eligible:
                eligible_count += 1
            elif lead.status == "scheduled":
                blocked[result.blocked_reason or "unknown"] += 1

        checks.append(
            self._check(
                "eligible_audience",
                "Eligible audience",
                "pass" if eligible_count > 0 else "fail",
                "critical" if eligible_count == 0 else "info",
                f"{eligible_count} scheduled lead(s) are eligible after verification, suppression, contact type, and compliance checks.",
                "Add or verify at least one eligible scheduled lead." if eligible_count == 0 else None,
                {"blocked_breakdown": dict(blocked), "audience_summary": audience},
            )
        )
        if audience["risky_count"] > 0:
            checks.append(
                self._check(
                    "risky_audience",
                    "Risky audience",
                    "warning",
                    "warning",
                    f"{audience['risky_count']} reachable lead(s) are marked risky.",
                    "Review risky leads before scaling this campaign.",
                    audience,
                )
            )
        if audience["suppressed_count"] > 0 or audience["unsubscribed_count"] > 0:
            checks.append(
                self._check(
                    "suppression_hygiene",
                    "Suppression hygiene",
                    "warning",
                    "warning",
                    f"{audience['suppressed_count']} suppressed and {audience['unsubscribed_count']} unsubscribed contact(s) are attached.",
                    "Suppressed and unsubscribed contacts will be excluded; clean lists before scaling.",
                    audience,
                )
            )

        blockers, warnings = self._issues_from_checks(checks, source="campaign", entity=campaign.name)
        status = self._status_from_issues(blockers, warnings, checks)
        return {
            "id": str(campaign.id),
            "type": "campaign",
            "name": campaign.name,
            "status": status,
            "score": self._score_from_checks(checks),
            "campaign_status": campaign.status,
            "mailbox": mailbox_payload,
            "audience": audience,
            "eligible_leads": eligible_count,
            "blockers": blockers,
            "warnings": warnings,
            "next_actions": self._next_actions(blockers, warnings),
            "checks": checks,
            "last_checked_at": datetime.utcnow().isoformat(),
        }

    def campaigns_summary(self) -> dict[str, Any]:
        active = self.db.query(func.count(Campaign.id)).filter(Campaign.status == "active").scalar() or 0
        draft = self.db.query(func.count(Campaign.id)).filter(Campaign.status == "draft").scalar() or 0
        paused = self.db.query(func.count(Campaign.id)).filter(Campaign.status == "paused").scalar() or 0
        campaigns = self.db.query(Campaign).filter(Campaign.status.in_(["active", "paused"])).limit(25).all()
        items = [self.campaign_readiness(str(campaign.id)) for campaign in campaigns]
        blockers = self._top_items([issue for item in items for issue in item.get("blockers", [])])
        warnings = self._top_items([issue for item in items for issue in item.get("warnings", [])])
        return {
            "status": self._combine_statuses([item["status"] for item in items]) if items else "ready",
            "summary": {"active": active, "draft": draft, "paused": paused, "checked_campaigns": len(items)},
            "items": items,
            "blockers": blockers,
            "warnings": warnings,
        }

    def audience_summary(self) -> dict[str, Any]:
        contacts = self.db.query(Contact).all()
        summary = summarize_contacts_for_campaign(contacts, None)
        duplicates = self._duplicate_contact_count()
        summary["duplicate_count"] = duplicates
        summary["disposable_count"] = sum(1 for contact in contacts if contact.is_disposable)
        summary["role_based_count"] = sum(1 for contact in contacts if contact.is_role_based)
        summary["unknown_count"] = sum(1 for contact in contacts if (contact.email_status or "unverified") == "unverified")

        warnings: list[dict[str, Any]] = []
        blockers: list[dict[str, Any]] = []
        if summary["lead_count"] == 0:
            warnings.append(self._issue("no_contacts", "warning", "No contacts exist yet, so audience deliverability cannot be evaluated.", "Import and verify contacts.", "audience"))
        if summary["suppressed_count"] > 0:
            warnings.append(self._issue("suppressed_contacts", "warning", f"{summary['suppressed_count']} suppressed contacts exist.", "Keep suppressed contacts excluded from campaigns.", "audience"))
        if summary["invalid_count"] > 0:
            warnings.append(self._issue("invalid_contacts", "warning", f"{summary['invalid_count']} contacts are invalid or blocked by verification.", "Remove invalid contacts from active lists.", "audience"))
        if summary["unknown_count"] > 0:
            warnings.append(self._issue("unverified_contacts", "warning", f"{summary['unknown_count']} contacts are still unverified.", "Run verification before campaign launch.", "audience"))

        status = "warning" if warnings else "ready"
        return {
            "status": status,
            "summary": summary,
            "blockers": blockers,
            "warnings": warnings,
            "next_actions": self._next_actions(blockers, warnings),
        }

    def warmup_summary(self) -> dict[str, Any]:
        setting = self.db.query(WarmupSetting).order_by(WarmupSetting.created_at.asc()).first()
        enabled = bool(setting and setting.is_enabled)
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        success = self.db.query(func.count(WarmupEvent.id)).filter(WarmupEvent.event_type == "send", WarmupEvent.created_at >= today, WarmupEvent.status == "success").scalar() or 0
        failed = self.db.query(func.count(WarmupEvent.id)).filter(WarmupEvent.event_type == "send", WarmupEvent.created_at >= today, WarmupEvent.status == "failed").scalar() or 0
        active_pairs = self.db.query(func.count(WarmupPair.id)).filter(WarmupPair.is_active == True).scalar() or 0
        enabled_mailboxes = self.db.query(func.count(Mailbox.id)).filter(Mailbox.warmup_enabled == True).scalar() or 0
        ready_mailboxes = self.db.query(func.count(Mailbox.id)).filter(Mailbox.warmup_enabled == True, Mailbox.warmup_status == "ready").scalar() or 0
        last_event = self.db.query(WarmupEvent).order_by(WarmupEvent.created_at.desc()).first()

        blockers: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        if not enabled:
            warnings.append(self._issue("warmup_paused", "warning", "Warm-up is paused globally.", "Start warm-up after at least two healthy mailboxes are ready.", "warmup"))
        if enabled_mailboxes < 2:
            warnings.append(self._issue("insufficient_warmup_mailboxes", "warning", "Fewer than two mailboxes have warm-up enabled.", "Enable warm-up on at least two SMTP-healthy mailboxes.", "warmup"))
        elif ready_mailboxes < 2:
            warnings.append(self._issue("warmup_mailboxes_not_ready", "warning", "Fewer than two warm-up-enabled mailboxes are currently ready.", "Fix mailbox SMTP/provider blockers.", "warmup"))
        if failed > 0 and success == 0:
            warnings.append(self._issue("warmup_failures_today", "warning", "Warm-up sends failed today and no successful warm-up sends are recorded.", "Inspect warm-up logs and SMTP/provider diagnostics.", "warmup"))

        return {
            "status": "warning" if warnings else "ready",
            "summary": {
                "global_status": "enabled" if enabled else "paused",
                "enabled_mailboxes": enabled_mailboxes,
                "ready_mailboxes": ready_mailboxes,
                "active_pairs": active_pairs,
                "successful_sends_today": success,
                "failed_sends_today": failed,
                "health_percent": int((success / (success + failed)) * 100) if success + failed else None,
                "last_activity_at": self._iso(last_event.created_at if last_event else None),
            },
            "blockers": blockers,
            "warnings": warnings,
            "next_actions": self._next_actions(blockers, warnings),
        }

    def provider_summary(self) -> dict[str, Any]:
        settings_row = ProviderSettingsService(self.db).get_or_create()
        enabled_map = {
            "mailcow": settings_row.mailcow_enabled,
            "google_workspace": settings_row.google_workspace_enabled,
        }
        items = []
        blockers: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        for provider_type, enabled in enabled_map.items():
            mailbox_count = self.db.query(func.count(Mailbox.id)).filter(Mailbox.provider_type == provider_type).scalar() or 0
            try:
                health = self.providers.get_provider(provider_type).check_provider_health()
            except Exception as exc:
                health = {"status": "failed", "configured": False, "detail": str(exc), "reason": "provider_check_failed"}
            item_status = "ready" if enabled and health.get("configured") and health.get("status") in {"healthy", "verified", "ready"} else "warning"
            if not enabled and mailbox_count > 0:
                issue = self._issue("provider_disabled", "critical", f"{provider_type.replace('_', ' ')} is disabled but {mailbox_count} mailbox(es) use it.", "Enable the provider or move those mailboxes before sending.", "provider", provider_type)
                blockers.append(issue)
                item_status = "blocked"
            elif enabled and not health.get("configured"):
                issue = self._issue("provider_misconfigured", "critical", health.get("detail") or f"{provider_type} is not configured.", "Complete backend provider configuration.", "provider", provider_type)
                blockers.append(issue)
                item_status = "blocked"
            elif enabled and health.get("status") not in {"healthy", "verified", "ready"}:
                issue = self._issue("provider_degraded", "warning", health.get("detail") or f"{provider_type} health is {health.get('status')}.", "Run provider diagnostics and resolve the reported issue.", "provider", provider_type)
                warnings.append(issue)
                item_status = "warning"
            items.append(
                {
                    "provider_type": provider_type,
                    "enabled": enabled,
                    "configured": bool(health.get("configured")),
                    "status": item_status,
                    "health_status": health.get("status"),
                    "detail": health.get("detail"),
                    "reason": health.get("reason"),
                    "mailbox_count": mailbox_count,
                    "checked_at": datetime.utcnow().isoformat(),
                }
            )
        return {
            "status": self._status_from_issues(blockers, warnings, []),
            "summary": {item["provider_type"]: {"enabled": item["enabled"], "configured": item["configured"], "status": item["status"], "mailbox_count": item["mailbox_count"]} for item in items},
            "items": items,
            "blockers": blockers,
            "warnings": warnings,
        }

    def legacy_summary(self) -> dict[str, int]:
        cutoff = datetime.utcnow() - timedelta(days=30)
        events = (
            self.db.query(DeliverabilityEvent.event_type, func.count(DeliverabilityEvent.id))
            .filter(DeliverabilityEvent.occurred_at >= cutoff)
            .group_by(DeliverabilityEvent.event_type)
            .all()
        )
        result = {"sent": 0, "replied": 0, "bounced": 0, "suppressed": 0}
        for event_type, count in events:
            if event_type in result:
                result[event_type] = count
        audience = self.audience_summary()["summary"]
        result.update(
            {
                "total_contacts": audience["lead_count"],
                "valid_contacts": audience["status_counts"].get("valid", 0),
                "risky_contacts": audience["risky_count"],
                "invalid_contacts": audience["invalid_count"],
                "suppressed_contacts": audience["suppressed_count"],
                "unsubscribed_contacts": audience["unsubscribed_count"],
                "b2b_campaigns": self.db.query(func.count(Campaign.id)).filter(Campaign.campaign_type == "b2b").scalar() or 0,
                "b2c_campaigns": self.db.query(func.count(Campaign.id)).filter(Campaign.campaign_type == "b2c").scalar() or 0,
                "active_campaigns": self.db.query(func.count(Campaign.id)).filter(Campaign.status == "active").scalar() or 0,
                "mailbox_count": self.db.query(func.count(Mailbox.id)).scalar() or 0,
                "domain_count": self.db.query(func.count(Domain.id)).scalar() or 0,
            }
        )
        return result

    def legacy_mailbox_stats(self) -> list[dict[str, Any]]:
        return [
            {
                "mailbox": item["email"],
                "sent": item["recent_sends"]["success_30d"],
                "replied": 0,
                "bounced": item["recent_sends"]["failed_30d"],
                "health_status": item["status"],
                "provider_type": item["provider_type"],
                "blockers": item["blockers"],
                "warnings": item["warnings"],
            }
            for item in self.mailboxes()["items"]
        ]

    def _domain_dns_check(self, domain: Domain, key: str, label: str, *, blocker: bool) -> dict[str, Any]:
        status = getattr(domain, f"{key}_status", None) or "pending"
        dns_results = domain.dns_results or {}
        result = dns_results.get(key, {}) if isinstance(dns_results, dict) else {}
        if status == "configured":
            return self._check(key, label, "pass", "info", result.get("detail") or f"{label} is configured.", None, {"records": result.get("records", [])}, domain.dns_last_checked_at)
        if status in {"missing", "failed"}:
            return self._check(
                key,
                label,
                "fail" if blocker else "warning",
                "critical" if blocker else "warning",
                result.get("detail") or f"{label} is {status}.",
                result.get("required_configuration", {}).get("explanation") or f"Configure a valid {label}.",
                result,
                domain.dns_last_checked_at,
            )
        return self._check(key, label, "warning", "warning", f"{label} has not been checked yet.", "Run domain verification.", result, domain.dns_last_checked_at)

    def _domain_bimi_check(self, domain: Domain) -> dict[str, Any]:
        dns_results = domain.dns_results or {}
        bimi = dns_results.get("bimi") if isinstance(dns_results, dict) else None
        if isinstance(bimi, dict) and bimi.get("status") == "configured":
            return self._check("bimi", "BIMI readiness", "pass", "info", bimi.get("detail") or "BIMI record is configured.", None, bimi, domain.dns_last_checked_at)
        return self._check("bimi", "BIMI readiness", "warning", "info", "BIMI has not been checked or configured. This is optional for sending readiness.", "Add BIMI later if brand indicators are required.", bimi or {}, domain.dns_last_checked_at)

    def _domain_provider_check(self, domain: Domain) -> dict[str, Any]:
        if domain.mailcow_status in {"verified", "pending", None}:
            return self._check("provider_visibility", "Provider visibility", "pass" if domain.mailcow_status == "verified" else "warning", "info" if domain.mailcow_status == "verified" else "warning", domain.mailcow_detail or f"Provider visibility is {domain.mailcow_status or 'not checked'}.", "Verify the domain with the configured mail provider." if domain.mailcow_status != "verified" else None, None, domain.mailcow_last_checked_at)
        return self._check("provider_visibility", "Provider visibility", "fail", "critical", domain.mailcow_detail or f"Provider visibility is {domain.mailcow_status}.", "Fix provider domain visibility before sending.", None, domain.mailcow_last_checked_at)

    def _mailbox_status_check(self, mailbox: Mailbox) -> dict[str, Any]:
        if mailbox.status == "active":
            return self._check("mailbox_active", "Mailbox active", "pass", "info", "Mailbox is active.")
        return self._check("mailbox_active", "Mailbox active", "fail", "critical", f"Mailbox is {mailbox.status}.", "Activate the mailbox before sending.")

    def _mailbox_provider_check(self, mailbox: Mailbox) -> dict[str, Any]:
        provider_type = mailbox.provider_type or "mailcow"
        try:
            self.providers.resolve_mailbox_provider(mailbox)
        except ProviderUnavailableError as exc:
            return self._check("provider_available", "Provider available", "fail", "critical", exc.message, "Enable or configure the mailbox provider.", {"category": exc.category}, mailbox.last_provider_check_at)
        if mailbox.provider_config_status not in {None, "configured"}:
            return self._check("provider_config", "Provider configuration", "fail", "critical", f"Provider configuration is {mailbox.provider_config_status}.", "Fix mailbox provider configuration.", None, mailbox.last_provider_check_at)
        if mailbox.last_provider_check_status in {"failed", "blocked", "unhealthy"}:
            return self._check("provider_health", "Provider health", "fail", "critical", mailbox.last_provider_check_message or "Last provider check failed.", "Run provider diagnostics.", None, mailbox.last_provider_check_at)
        return self._check("provider_available", "Provider available", "pass", "info", f"{provider_type.replace('_', ' ')} is available for this mailbox.", None, None, mailbox.last_provider_check_at)

    def _mailbox_oauth_check(self, mailbox: Mailbox) -> dict[str, Any]:
        if (mailbox.provider_type or "mailcow") != "google_workspace":
            return self._check("oauth", "OAuth connection", "pass", "info", "OAuth is not required for this provider.")
        status = mailbox.oauth_connection_status or (mailbox.oauth_token.connection_status if mailbox.oauth_token else "not_connected")
        if status == "connected":
            return self._check("oauth", "OAuth connection", "pass", "info", "Google Workspace OAuth is connected.", None, None, mailbox.oauth_last_checked_at)
        return self._check("oauth", "OAuth connection", "fail", "critical", mailbox.oauth_last_error or f"Google Workspace OAuth is {status}.", "Connect or reconnect Google Workspace OAuth.", {"oauth_status": status}, mailbox.oauth_last_checked_at)

    def _mailbox_smtp_check(self, mailbox: Mailbox) -> dict[str, Any]:
        if mailbox.smtp_last_check_status == "healthy":
            return self._check("smtp", "SMTP health", "pass", "info", "SMTP diagnostics passed.", None, {"category": mailbox.smtp_last_check_category}, mailbox.smtp_last_checked_at)
        if mailbox.smtp_last_check_status:
            return self._check("smtp", "SMTP health", "fail", "critical", mailbox.smtp_last_check_message or f"SMTP is {mailbox.smtp_last_check_status}.", "Run SMTP diagnostics and fix the reported issue.", {"category": mailbox.smtp_last_check_category}, mailbox.smtp_last_checked_at)
        return self._check("smtp", "SMTP health", "warning", "warning", "SMTP has not been checked yet.", "Run SMTP diagnostics before campaign sending.", None, mailbox.smtp_last_checked_at)

    def _mailbox_imap_check(self, mailbox: Mailbox) -> dict[str, Any]:
        if not mailbox.inbox_sync_enabled:
            return self._check("imap", "IMAP/inbox sync", "warning", "warning", "Inbox sync is disabled for this mailbox.", "Enable inbox sync if replies should be tracked.", None, mailbox.inbox_last_synced_at)
        if mailbox.inbox_sync_status in {"healthy", "success", "completed"}:
            return self._check("imap", "IMAP/inbox sync", "pass", "info", "Inbox sync has succeeded.", None, None, mailbox.inbox_last_success_at)
        if mailbox.inbox_sync_status in {"failed", "blocked"}:
            return self._check("imap", "IMAP/inbox sync", "warning", "warning", mailbox.inbox_last_error or "Inbox sync is failing.", "Run inbox sync diagnostics.", None, mailbox.inbox_last_synced_at)
        return self._check("imap", "IMAP/inbox sync", "warning", "info", "Inbox sync has not run yet.", "Run inbox sync if reply visibility is required.", None, mailbox.inbox_last_synced_at)

    def _mailbox_warmup_check(self, mailbox: Mailbox) -> dict[str, Any]:
        if not mailbox.warmup_enabled:
            return self._check("warmup", "Warm-up posture", "warning", "info", "Warm-up is disabled for this mailbox.", "Enable warm-up for new or cold mailboxes before scaling.", None, mailbox.warmup_last_checked_at)
        if mailbox.warmup_status == "ready":
            return self._check("warmup", "Warm-up posture", "pass", "info", mailbox.warmup_last_result or "Mailbox is eligible for warm-up.", None, None, mailbox.warmup_last_checked_at)
        return self._check("warmup", "Warm-up posture", "warning", "warning", mailbox.warmup_block_reason or f"Warm-up status is {mailbox.warmup_status or 'unknown'}.", "Fix warm-up blocker before scaling sending.", None, mailbox.warmup_last_checked_at)

    def _mailbox_recent_send_check(self, mailbox: Mailbox) -> dict[str, Any]:
        counts = self._recent_send_counts(mailbox.id)
        attempts = counts["success_7d"] + counts["failed_7d"]
        if attempts == 0:
            return self._check("recent_send_posture", "Recent send posture", "warning", "info", "No recent send results are recorded for this mailbox.", "Send a controlled direct test before campaign launch.", counts)
        fail_rate = counts["failed_7d"] / attempts
        if counts["success_7d"] == 0 and counts["failed_7d"] > 0:
            return self._check("recent_send_posture", "Recent send posture", "fail", "critical", "Recent sends are failing and no successful sends are recorded.", "Fix SMTP/provider errors before sending campaigns.", counts)
        if fail_rate > 0.3:
            return self._check("recent_send_posture", "Recent send posture", "warning", "warning", f"Recent send failure rate is {int(fail_rate * 100)}%.", "Review send logs and lower sending volume until stable.", counts)
        return self._check("recent_send_posture", "Recent send posture", "pass", "info", "Recent sends are within acceptable failure bounds.", None, counts)

    def _recent_send_counts(self, mailbox_id: Any) -> dict[str, int | str | None]:
        now = datetime.utcnow()
        cutoff_7 = now - timedelta(days=7)
        cutoff_30 = now - timedelta(days=30)
        success_7 = self.db.query(func.count(SendLog.id)).filter(SendLog.mailbox_id == mailbox_id, SendLog.created_at >= cutoff_7, SendLog.delivery_status == "success").scalar() or 0
        failed_7 = self.db.query(func.count(SendLog.id)).filter(SendLog.mailbox_id == mailbox_id, SendLog.created_at >= cutoff_7, SendLog.delivery_status == "failed").scalar() or 0
        success_30 = self.db.query(func.count(SendLog.id)).filter(SendLog.mailbox_id == mailbox_id, SendLog.created_at >= cutoff_30, SendLog.delivery_status == "success").scalar() or 0
        failed_30 = self.db.query(func.count(SendLog.id)).filter(SendLog.mailbox_id == mailbox_id, SendLog.created_at >= cutoff_30, SendLog.delivery_status == "failed").scalar() or 0
        last = self.db.query(SendLog).filter(SendLog.mailbox_id == mailbox_id).order_by(SendLog.created_at.desc()).first()
        return {
            "success_7d": success_7,
            "failed_7d": failed_7,
            "success_30d": success_30,
            "failed_30d": failed_30,
            "last_status": last.delivery_status if last else None,
            "last_error": last.smtp_response if last and last.delivery_status == "failed" else None,
            "last_sent_at": self._iso(last.created_at if last else None),
        }

    def _duplicate_contact_count(self) -> int:
        rows = self.db.query(Contact.email, func.count(Contact.id)).group_by(Contact.email).having(func.count(Contact.id) > 1).all()
        return sum(count - 1 for _, count in rows)

    def _collection_payload(self, items: list[dict[str, Any]], count_key: str) -> dict[str, Any]:
        blockers = self._top_items([issue for item in items for issue in item.get("blockers", [])])
        warnings = self._top_items([issue for item in items for issue in item.get("warnings", [])], limit=10)
        statuses = Counter(item["status"] for item in items)
        return {
            "status": self._combine_statuses([item["status"] for item in items]) if items else "warning",
            "summary": {count_key: len(items), "ready": statuses.get("ready", 0), "warning": statuses.get("warning", 0), "degraded": statuses.get("degraded", 0), "blocked": statuses.get("blocked", 0)},
            "items": items,
            "blockers": blockers,
            "warnings": warnings,
            "next_actions": self._next_actions(blockers, warnings),
        }

    def _check(
        self,
        code: str,
        label: str,
        status: str,
        severity: str,
        detail: str,
        next_action: str | None = None,
        metadata: Any | None = None,
        checked_at: datetime | None = None,
    ) -> dict[str, Any]:
        return {
            "code": code,
            "label": label,
            "status": status,
            "severity": severity,
            "detail": detail,
            "next_action": next_action,
            "metadata": metadata,
            "checked_at": self._iso(checked_at),
        }

    def _issue(self, code: str, severity: str, message: str, next_action: str | None, source: str, entity: str | None = None) -> dict[str, Any]:
        return {
            "code": code,
            "severity": severity,
            "message": message,
            "next_action": next_action,
            "source": source,
            "entity": entity,
        }

    def _issues_from_checks(self, checks: list[dict[str, Any]], *, source: str, entity: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        blockers = []
        warnings = []
        for check in checks:
            if check["status"] == "fail" and check["severity"] == "critical":
                blockers.append(self._issue(check["code"], check["severity"], check["detail"], check.get("next_action"), source, entity))
            elif check["status"] in {"warning", "fail"}:
                warnings.append(self._issue(check["code"], check["severity"], check["detail"], check.get("next_action"), source, entity))
        return blockers, warnings

    def _status_from_issues(self, blockers: list[dict[str, Any]], warnings: list[dict[str, Any]], checks: list[dict[str, Any]]) -> str:
        if blockers:
            return "blocked"
        if any(issue.get("severity") == "warning" for issue in warnings):
            return "degraded"
        if warnings:
            return "warning"
        if not checks:
            return "unknown"
        return "ready"

    def _combine_statuses(self, statuses: list[str]) -> str:
        if not statuses:
            return "unknown"
        return max(statuses, key=lambda status: READINESS_ORDER.get(status, 1))

    def _score_from_status(self, status: str) -> int | None:
        return {"ready": 100, "warning": 75, "degraded": 45, "blocked": 0}.get(status)

    def _score_from_checks(self, checks: list[dict[str, Any]]) -> int | None:
        scored = [check for check in checks if check["severity"] != "info" or check["status"] == "pass"]
        if not scored:
            return None
        weights = {"pass": 1.0, "warning": 0.6, "fail": 0.0}
        return int((sum(weights.get(check["status"], 0.5) for check in scored) / len(scored)) * 100)

    def _top_items(self, issues: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
        return issues[:limit]

    def _next_actions(self, blockers: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> list[str]:
        actions = []
        for issue in blockers + warnings:
            action = issue.get("next_action")
            if action and action not in actions:
                actions.append(action)
        return actions[:6]

    def _missing_entity(self, entity_type: str) -> dict[str, Any]:
        return {
            "type": entity_type,
            "status": "blocked",
            "score": 0,
            "blockers": [self._issue(f"{entity_type}_not_found", "critical", f"{entity_type.title()} not found.", None, entity_type)],
            "warnings": [],
            "next_actions": [],
            "checks": [],
        }

    def _iso(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None
