import dns.resolver
from sqlalchemy.orm import Session
from app.models.campaign import Campaign, CampaignLead, Contact
from app.models.monitoring import CampaignPreflightCheck
from app.services.list_service import LeadListService
from app.services.verification_service import contact_is_reachable

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

        # 3. Lead Quality Bounds
        active_leads = self.db.query(CampaignLead).join(Contact).filter(
            CampaignLead.campaign_id == campaign.id,
            CampaignLead.status == "scheduled"
        ).all()
        
        suppressed_count = sum(1 for cl in active_leads if cl.contact.is_suppressed)
        blocked_count = sum(1 for cl in active_leads if not contact_is_reachable(cl.contact))

        if suppressed_count > 0 or blocked_count > (len(active_leads) * 0.2):
            checks.append(CampaignPreflightCheck(
                campaign_id=campaign.id,
                check_name="lead_quality",
                status="fail",
                severity="critical",
                message=f"Campaign contains {suppressed_count} suppressed leads and {blocked_count} leads that are not verified for outreach. Launch Blocked."
            ))
        else:
            checks.append(CampaignPreflightCheck(
                campaign_id=campaign.id,
                check_name="lead_quality",
                status="pass",
                severity="info",
                message="Lead quality metrics within acceptable bounds."
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
                {"name": c.check_name, "status": c.status, "message": c.message} 
                for c in checks
            ],
            "list_summary": list_summary,
        }
