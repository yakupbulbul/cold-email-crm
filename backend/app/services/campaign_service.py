from sqlalchemy.orm import Session
from app.models.campaign import Campaign, CampaignLead, SendLog
from app.services.smtp_service import SMTPManagerService
from app.schemas.email import SendEmailRequest
from datetime import datetime
import logging

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

    def _process_campaign(self, campaign: Campaign):
        today = datetime.utcnow().date()
        
        sent_today = self.db.query(SendLog).filter(
            SendLog.campaign_id == campaign.id,
            SendLog.created_at >= today
        ).count()
        
        if sent_today >= campaign.daily_limit:
            return
            
        pending_leads = self.db.query(CampaignLead).filter(
            CampaignLead.campaign_id == campaign.id,
            CampaignLead.status == "scheduled"
        ).limit(campaign.daily_limit - sent_today).all()

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
            success, message_id = self.smtp.send_email(req)
            
            lead.status = "sent" if success else "failed"
            lead.sent_at = datetime.utcnow() if success else None
            
            log = SendLog(
                mailbox_id=campaign.mailbox_id,
                campaign_id=campaign.id,
                contact_id=lead.contact_id,
                target_email=lead.contact.email,
                subject=subject,
                delivery_status="success" if success else "failed",
                smtp_response=message_id
            )
            self.db.add(log)
            self.db.add(lead)
            self.db.commit()
