import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.campaign import Campaign, CampaignLead, SendLog
from app.schemas.email import SendEmailRequest
from app.services.audience_service import evaluate_contact_for_campaign
from app.services.list_service import LeadListService
from app.services.smtp_service import SMTPManagerService, SMTPServiceError

logger = logging.getLogger(__name__)

class CampaignService:
    def __init__(self, db: Session):
        self.db = db
        self.smtp = SMTPManagerService(db)

    def process_active_campaigns(self):
        active_campaigns = self.db.query(Campaign).filter(Campaign.status == "active").all()
        for c in active_campaigns:
            try:
                self._process_campaign(c)
            except Exception as e:
                logger.error(f"Error processing campaign {c.id}: {e}")

    def process_campaign_by_id(self, campaign_id: str) -> dict:
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            raise ValueError("Campaign not found")
        if campaign.status != "active":
            return {"campaign_id": str(campaign.id), "status": campaign.status, "processed": 0}
        processed = self._process_campaign(campaign)
        return {"campaign_id": str(campaign.id), "status": campaign.status, "processed": processed}

    def _process_campaign(self, campaign: Campaign):
        # Re-sync attached list members on every active cycle so transient SMTP
        # failures do not strand list-backed leads in a permanent failed state.
        LeadListService(self.db).sync_campaign_leads(str(campaign.id))

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        sent_today = self.db.query(SendLog).filter(
            SendLog.campaign_id == campaign.id,
            SendLog.created_at >= today
        ).count()

        if sent_today >= campaign.daily_limit:
            return 0

        from app.models.campaign import Contact
        pending_leads = self.db.query(CampaignLead).join(Contact).filter(
            CampaignLead.campaign_id == campaign.id,
            CampaignLead.status == "scheduled",
        ).limit(campaign.daily_limit - sent_today).all()
        pending_leads = [
            lead
            for lead in pending_leads
            if evaluate_contact_for_campaign(lead.contact, campaign).eligible
        ]

        processed_count = 0

        for lead in pending_leads:
            subject = campaign.template_subject.replace("{{first_name}}", lead.contact.first_name or "")
            body = campaign.template_body.replace("{{first_name}}", lead.contact.first_name or "")
            body = body.replace("{{company}}", lead.contact.company or "")
            
            req = SendEmailRequest(
                mailbox_id=campaign.mailbox_id,
                to=[lead.contact.email],
                subject=subject,
                text_body=body
            )
            try:
                success, response = self.smtp.send_email(req)
                message_id, log_id = response.split("|", 1)
                lead.status = "sent" if success else "failed"
                lead.sent_at = datetime.utcnow() if success else None
                log = self.db.query(SendLog).filter(SendLog.id == UUID(log_id)).first()
                if log:
                    log.campaign_id = campaign.id
                    log.contact_id = lead.contact_id
                    log.subject = subject
                    self.db.add(log)
            except SMTPServiceError as exc:
                logger.warning("Campaign send failed for %s via %s: %s", lead.contact.email, campaign.id, exc.message)
                lead.status = "failed"
                lead.sent_at = None
                if exc.log_id:
                    log = self.db.query(SendLog).filter(SendLog.id == UUID(exc.log_id)).first()
                    if log:
                        log.campaign_id = campaign.id
                        log.contact_id = lead.contact_id
                        log.subject = subject
                        self.db.add(log)
            processed_count += 1
            self.db.add(lead)
            self.db.commit()

        return processed_count
