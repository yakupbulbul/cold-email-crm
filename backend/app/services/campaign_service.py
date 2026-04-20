import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from app.models.campaign import Campaign, CampaignLead, CampaignSequenceStep, Contact, SendLog
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
        active_campaigns = self.db.query(Campaign).options(selectinload(Campaign.sequence_steps)).filter(Campaign.status == "active").all()
        for c in active_campaigns:
            try:
                self._process_campaign(c)
            except Exception as e:
                logger.error(f"Error processing campaign {c.id}: {e}")

    def process_campaign_by_id(self, campaign_id: str) -> dict:
        campaign = self.db.query(Campaign).options(selectinload(Campaign.sequence_steps)).filter(Campaign.id == campaign_id).first()
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
            SendLog.created_at >= today,
            SendLog.delivery_status == "success",
        ).count()

        if sent_today >= campaign.daily_limit:
            return 0

        pending_leads = self.db.query(CampaignLead).join(Contact).filter(
            CampaignLead.campaign_id == campaign.id,
            CampaignLead.status == "scheduled",
            or_(CampaignLead.scheduled_at == None, CampaignLead.scheduled_at <= datetime.utcnow()),
        ).limit(campaign.daily_limit - sent_today).all()
        pending_leads = [
            lead
            for lead in pending_leads
            if evaluate_contact_for_campaign(lead.contact, campaign).eligible
        ]

        processed_count = 0

        for lead in pending_leads:
            step = self._current_sequence_step(campaign, lead)
            if not step:
                lead.status = "sent"
                self.db.add(lead)
                self.db.commit()
                continue

            if step.stop_on_reply and (lead.replied_at or lead.contact.last_replied_at):
                lead.status = "replied"
                self.db.add(lead)
                self.db.commit()
                continue

            subject = self._render_template(step.subject, lead.contact)
            body = self._render_template(step.body, lead.contact)
            
            req = SendEmailRequest(
                mailbox_id=campaign.mailbox_id,
                to=[lead.contact.email],
                subject=subject,
                text_body=body,
                campaign_id=campaign.id,
                contact_id=lead.contact_id,
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
                if success:
                    self._schedule_next_step(campaign, lead)
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

    def _sequence_steps(self, campaign: Campaign) -> list[CampaignSequenceStep]:
        steps = sorted(campaign.sequence_steps or [], key=lambda item: item.step_number)
        if steps:
            return steps
        return [
            CampaignSequenceStep(
                campaign_id=campaign.id,
                step_number=1,
                delay_days=0,
                subject=campaign.template_subject,
                body=campaign.template_body,
                stop_on_reply=True,
            )
        ]

    def _current_sequence_step(self, campaign: Campaign, lead: CampaignLead) -> CampaignSequenceStep | None:
        current_step_number = lead.sequence_step_index or 1
        return next((step for step in self._sequence_steps(campaign) if step.step_number == current_step_number), None)

    def _schedule_next_step(self, campaign: Campaign, lead: CampaignLead) -> None:
        steps = self._sequence_steps(campaign)
        current_step_number = lead.sequence_step_index or 1
        next_step = next((step for step in steps if step.step_number > current_step_number), None)
        lead.sent_at = datetime.utcnow()
        if next_step:
            lead.sequence_step_index = next_step.step_number
            lead.status = "scheduled"
            lead.scheduled_at = datetime.utcnow() + timedelta(days=max(next_step.delay_days, 0))
        else:
            lead.status = "sent"
            lead.scheduled_at = None

    def _render_template(self, value: str, contact: Contact) -> str:
        replacements = {
            "{{first_name}}": contact.first_name or "",
            "{{last_name}}": contact.last_name or "",
            "{{company}}": contact.company or "",
            "{{email}}": contact.email or "",
            "{{job_title}}": contact.job_title or "",
            "{{website}}": contact.website or "",
        }
        rendered = value
        for token, replacement in replacements.items():
            rendered = rendered.replace(token, replacement)
        return rendered
