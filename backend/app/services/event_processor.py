import logging
from sqlalchemy.orm import Session
from app.models.monitoring import DeliverabilityEvent
from app.models.campaign import CampaignLead, Contact
from app.models.suppression import SuppressionList

logger = logging.getLogger(__name__)

class EventProcessorService:
    def __init__(self, db: Session):
        self.db = db

    def process_hard_bounce(self, event_id: str):
        """Processes a Hard Bounce event, forcibly moving the contact to the Global Suppression List"""
        event = self.db.query(DeliverabilityEvent).filter(DeliverabilityEvent.id == event_id).first()
        if not event or not event.contact_id:
            return

        contact = self.db.query(Contact).filter(Contact.id == event.contact_id).first()
        if not contact:
            return

        # Explicitly suppress the contact
        contact.is_suppressed = True
        
        # Add to global suppression DB
        existing_sup = self.db.query(SuppressionList).filter(SuppressionList.email == contact.email).first()
        if not existing_sup:
            sup = SuppressionList(
                email=contact.email,
                reason="hard_bounce",
                source="auto_bounce_processor",
                notes=f"Automated suppression via SMTP Response: {event.smtp_response[:100] if event.smtp_response else 'Unknown'}"
            )
            self.db.add(sup)
            
        # Update active campaign leads to failed
        active_leads = self.db.query(CampaignLead).filter(
            CampaignLead.contact_id == contact.id,
            CampaignLead.status == "scheduled"
        ).all()
        for cl in active_leads:
            cl.status = "failed"
            
        self.db.commit()
        logger.info(f"Contact {contact.email} globally suppressed due to Hard Bounce (Event: {event_id})")

    def process_complaint(self, event_id: str):
        """Processes a Spam Complaint, aggressively blocking and removing the contact"""
        event = self.db.query(DeliverabilityEvent).filter(DeliverabilityEvent.id == event_id).first()
        if not event or not event.contact_id:
            return

        contact = self.db.query(Contact).filter(Contact.id == event.contact_id).first()
        if not contact:
            return

        contact.is_suppressed = True
        existing_sup = self.db.query(SuppressionList).filter(SuppressionList.email == contact.email).first()
        if not existing_sup:
            self.db.add(SuppressionList(
                email=contact.email,
                reason="complaint",
                source="auto_complaint_processor",
                notes="Automated suppression triggered by explicitly identified ISP complaint string."
            ))
            
        self.db.commit()
        logger.warning(f"CRITICAL: Spam Complaint processed for {contact.email}. Globally Suppressed.")

    def process_unsubscribe(self, event_id: str):
        """Suppresses a contact that requested to unsubscribe via reply keyword."""
        event = self.db.query(DeliverabilityEvent).filter(DeliverabilityEvent.id == event_id).first()
        if not event or not event.contact_id:
            return
        contact = self.db.query(Contact).filter(Contact.id == event.contact_id).first()
        if not contact:
            return
        contact.is_suppressed = True
        existing_sup = self.db.query(SuppressionList).filter(SuppressionList.email == contact.email).first()
        if not existing_sup:
            self.db.add(SuppressionList(
                email=contact.email,
                reason="unsubscribe",
                source="auto_unsubscribe_processor",
                notes="Automated suppression triggered by unsubscribe reply keyword.",
            ))
        self.db.commit()
        logger.info(f"Contact {contact.email} suppressed due to unsubscribe request (Event: {event_id})")

    def process_reply(self, event_id: str, reply_text: str):
        """Classifies incoming IMAP replies mapping them to Campaign structures"""
        event = self.db.query(DeliverabilityEvent).filter(DeliverabilityEvent.id == event_id).first()
        if not event or not event.contact_id:
            return

        contact = self.db.query(Contact).filter(Contact.id == event.contact_id).first()
        if not contact:
            return
            
        l_text = reply_text.lower()
        classification = "interested"
        
        # Very basic MVP classification
        if any(word in l_text for word in ["unsubscribe", "remove me", "stop", "opt out"]):
            classification = "unsubscribe"
            self.process_unsubscribe(event_id)
        elif any(word in l_text for word in ["not interested", "no thanks"]):
            classification = "not_interested"
            
        event.metadata_blob = {"auto_classification": classification, "partial_text": reply_text[:200]}
        
        if classification in ["interested", "not_interested"]:
            active_lead = self.db.query(CampaignLead).filter(CampaignLead.contact_id == contact.id).order_by(CampaignLead.created_at.desc()).first()
            if active_lead:
                active_lead.status = "replied"
                active_lead.replied_at = event.occurred_at
                
        self.db.commit()
