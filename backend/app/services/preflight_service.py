import dns.resolver
from sqlalchemy.orm import Session
from app.models.campaign import Campaign, CampaignLead, Contact
from app.models.monitoring import CampaignPreflightCheck
from app.services.audience_service import summarize_contacts_for_campaign
from app.services.deliverability_service import DeliverabilityService
from app.services.list_service import LeadListService

class PreflightService:
    def __init__(self, db: Session):
        self.db = db

    def check_spf(self, domain: str) -> bool:
        try:
            answers = dns.resolver.resolve(domain, 'TXT')
            for rdata in answers:
                if "v=spf1" in rdata.to_text():
                    return True
        except Exception:
            pass
        return False

    def check_dmarc(self, domain: str) -> bool:
        try:
            answers = dns.resolver.resolve(f"_dmarc.{domain}", 'TXT')
            for rdata in answers:
                if "v=DMARC1" in rdata.to_text():
                    return True
        except Exception:
            pass
        return False

    def run_preflight(self, campaign_id: str) -> dict:
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign or not campaign.mailbox:
            return {"status": "fail", "checks": []}
            
        domain = campaign.mailbox.email.split('@')[1]
        
        checks = []
        list_service = LeadListService(self.db)
        list_summary = list_service.summarize_campaign_lists(str(campaign.id))
        
        # 1. SPF Check
        has_spf = self.check_spf(domain)
        checks.append(CampaignPreflightCheck(
            campaign_id=campaign.id,
            check_name="spf_validation",
            status="pass" if has_spf else "warning",
            severity="warning",
            message=f"SPF record {'found' if has_spf else 'missing'} for {domain}"
        ))

        # 2. DMARC Check
        has_dmarc = self.check_dmarc(domain)
        checks.append(CampaignPreflightCheck(
            campaign_id=campaign.id,
            check_name="dmarc_validation",
            status="pass" if has_dmarc else "warning",
            severity="warning",
            message=f"DMARC record {'found' if has_dmarc else 'missing'} for {domain}"
        ))

        deliverability = DeliverabilityService(self.db).campaign_readiness(str(campaign.id))
        deliverability_status = deliverability.get("status", "unknown")
        deliverability_blockers = deliverability.get("blockers", [])
        checks.append(CampaignPreflightCheck(
            campaign_id=campaign.id,
            check_name="deliverability_readiness",
            status="fail" if deliverability_status == "blocked" else "warning" if deliverability_status in {"warning", "degraded", "unknown"} else "pass",
            severity="critical" if deliverability_status == "blocked" else "warning" if deliverability_status in {"warning", "degraded", "unknown"} else "info",
            message=(
                f"Deliverability posture is {deliverability_status}. "
                + (
                    f"Primary blocker: {deliverability_blockers[0]['message']}"
                    if deliverability_blockers
                    else "No blocking infrastructure issues found."
                )
            ),
            metadata_blob=deliverability,
        ))

        # 3. Lead Quality Bounds
        active_leads = self.db.query(CampaignLead).join(Contact).filter(
            CampaignLead.campaign_id == campaign.id,
            CampaignLead.status == "scheduled"
        ).all()

        contact_summary = summarize_contacts_for_campaign([lead.contact for lead in active_leads], campaign)
        suppressed_count = contact_summary["suppressed_count"]
        blocked_count = contact_summary["invalid_count"]
        consent_unknown_count = contact_summary["consent_unknown_count"]
        type_mismatch_count = contact_summary["type_mismatch_count"]

        if suppressed_count > 0 or blocked_count > (len(active_leads) * 0.2):
            checks.append(CampaignPreflightCheck(
                campaign_id=campaign.id,
                check_name="lead_quality",
                status="fail",
                severity="critical",
                message=f"Campaign contains {suppressed_count} suppressed leads and {blocked_count} blocked leads after verification/compliance checks. Launch blocked.",
                metadata_blob=contact_summary,
            ))
        else:
            checks.append(CampaignPreflightCheck(
                campaign_id=campaign.id,
                check_name="lead_quality",
                status="pass",
                severity="info",
                message="Lead quality metrics within acceptable bounds.",
                metadata_blob=contact_summary,
            ))

        if campaign.campaign_type == "b2b":
            checks.append(CampaignPreflightCheck(
                campaign_id=campaign.id,
                check_name="b2b_audience_mix",
                status="warning" if contact_summary["risky_count"] > 0 else "pass",
                severity="warning" if contact_summary["risky_count"] > 0 else "info",
                message=f"B2B audience has {contact_summary['risky_count']} risky contacts, {contact_summary['high_quality_count']} high-quality contacts, and {sum(contact_summary['persona_counts'].values())} contacts with persona metadata.",
                metadata_blob={"persona_counts": contact_summary["persona_counts"], "industry_counts": contact_summary["industry_counts"]},
            ))
        else:
            strict_fail = campaign.compliance_mode == "strict_b2c" and (consent_unknown_count > 0 or contact_summary["unsubscribed_count"] > 0)
            checks.append(CampaignPreflightCheck(
                campaign_id=campaign.id,
                check_name="b2c_compliance",
                status="fail" if strict_fail else "warning" if (consent_unknown_count > 0 or type_mismatch_count > 0) else "pass",
                severity="critical" if strict_fail else "warning" if (consent_unknown_count > 0 or type_mismatch_count > 0) else "info",
                message=f"B2C audience includes {contact_summary['unsubscribed_count']} unsubscribed, {consent_unknown_count} consent-unknown, and {type_mismatch_count} type-mismatched contacts.",
                metadata_blob={
                    "consent_counts": contact_summary["consent_counts"],
                    "unsubscribe_counts": contact_summary["unsubscribe_counts"],
                    "type_mismatch_count": type_mismatch_count,
                },
            ))

        checks.append(CampaignPreflightCheck(
            campaign_id=campaign.id,
            check_name="list_coverage",
            status="pass" if list_summary["lead_count"] > 0 else "warning",
            severity="info" if list_summary["lead_count"] > 0 else "warning",
            message=f"Attached lists contribute {list_summary['lead_count']} deduplicated leads ({list_summary['reachable_count']} reachable, {list_summary['suppressed_count']} suppressed, {list_summary['invalid_count']} invalid/risky blockers).",
            metadata_blob=list_summary,
        ))
            
        self.db.add_all(checks)
        self.db.commit()

        overall_status = "pass"
        blocking_failures = False
        
        for c in checks:
            if c.status == "warning" and overall_status == "pass":
                overall_status = "warning"
            if c.status == "fail":
                overall_status = "fail"
                blocking_failures = True
                
        # If preflight fails critically, forcefully pause campaign if active
        if blocking_failures and campaign.status == "active":
            campaign.status = "paused"
            self.db.commit()

        return {
            "status": overall_status,
            "blocked": blocking_failures,
            "checks": [
                {
                    "name": c.check_name,
                    "status": c.status,
                    "severity": c.severity,
                    "message": c.message,
                    "metadata": c.metadata_blob,
                }
                for c in checks
            ],
            "list_summary": list_summary,
            "audience_summary": contact_summary,
        }
