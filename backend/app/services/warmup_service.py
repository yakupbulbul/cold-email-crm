import random
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.core import Mailbox
from app.models.warmup import WarmupPair, WarmupEvent
from app.services.smtp_service import SMTPManagerService
from app.schemas.email import SendEmailRequest

class WarmupPlanner:
    @staticmethod
    def get_daily_limit(mailbox: Mailbox) -> int:
        days_active = (datetime.utcnow() - mailbox.created_at).days
        if days_active <= 3:
            return 5
        elif days_active <= 7:
            return random.randint(8, 12)
        elif days_active <= 14:
            return random.randint(15, 20)
        return min(30, mailbox.daily_send_limit)

class WarmupSender:
    def __init__(self, db: Session):
        self.db = db
        self.smtp = SMTPManagerService(db)
        
    def send_warmup_email(self, pair: WarmupPair):
        subjects = ["Quick question", "Checking in", "Hello there", "Meeting next week?", "Following up on our chat"]
        bodies = ["Just wanted to reach out and say hi.", "Are you available for a quick chat?", "Hope you are doing well.", "Let me know your thoughts on this."]
        
        subject = random.choice(subjects)
        body = random.choice(bodies)
        
        today = datetime.utcnow().date()
        sent_today = self.db.query(WarmupEvent).filter(
            WarmupEvent.mailbox_id == pair.sender_mailbox_id,
            WarmupEvent.event_type == "send",
            WarmupEvent.created_at >= today
        ).count()
        
        limit = WarmupPlanner.get_daily_limit(pair.sender)
        if sent_today >= limit:
            return
            
        req = SendEmailRequest(
            mailbox_id=pair.sender_mailbox_id,
            to=[pair.recipient.email],
            subject=subject,
            text_body=body
        )
        success, response = self.smtp.send_email(req)
        
        event = WarmupEvent(
            mailbox_id=pair.sender_mailbox_id,
            event_type="send",
            target_email=pair.recipient.email,
            subject=subject,
            body_preview=body,
            status="success" if success else "failed",
            sent_at=datetime.utcnow() if success else None
        )
        self.db.add(event)
        self.db.commit()

class WarmupService:
    def __init__(self, db: Session):
        self.db = db
        
    def process_all_active_pairs(self, *, force_send: bool = False):
        active_pairs = self.db.query(WarmupPair).filter(WarmupPair.is_active == True).all()
        sender = WarmupSender(self.db)
        for pair in active_pairs:
            # Add explicit random delays natively to avoid bulk spam patterns
            if force_send or random.random() > 0.3:  # 70% chance to skip scheduled cycles to randomize sending
                sender.send_warmup_email(pair)
