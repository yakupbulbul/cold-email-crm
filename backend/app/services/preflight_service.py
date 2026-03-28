import dns.resolver
from sqlalchemy.orm import Session
from app.models.campaign import Campaign, CampaignLead, Contact
from app.models.monitoring import CampaignPreflightCheck

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
        unverified_count = sum(1 for cl in active_leads if cl.contact.verification_score < 80)
        
        if suppressed_count > 0 or unverified_count > (len(active_leads) * 0.2):
            # Critical blocker if more than 20% leads are unverified or any are explicitly suppressed
            checks.append(CampaignPreflightCheck(
                campaign_id=campaign.id,
                check_name="lead_quality",
                status="fail",
                severity="critical",
                message=f"Campaign contains {suppressed_count} suppressed leads and {unverified_count} risky leads. Launch Blocked."
            ))
        else:
            checks.append(CampaignPreflightCheck(
                campaign_id=campaign.id,
                check_name="lead_quality",
                status="pass",
                severity="info",
                message="Lead quality metrics within acceptable bounds."
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
            ]
        }
