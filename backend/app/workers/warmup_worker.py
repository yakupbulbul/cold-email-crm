from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.models import WarmupPair, WarmupEvent
from app.integrations.smtp.smtp_service import send_email
import random
import time

@celery_app.task
def process_warmups():
    db = SessionLocal()
    pairs = db.query(WarmupPair).filter(WarmupPair.is_active == True).all()
    
    for pair in pairs:
        # Determine direction randomly: A->B or B->A
        if random.choice([True, False]):
            sender, recipient = pair.mailbox_a, pair.mailbox_b
        else:
            sender, recipient = pair.mailbox_b, pair.mailbox_a
            
        subject = f"Following up {random.randint(1000, 9999)}"
        body = f"Hello, just wanted to check if you received my previous message. Let me know!"
        
        try:
            send_email(
                mailbox=sender,
                to_email=recipient.email,
                subject=subject,
                html_content=f"<p>{body}</p>",
                text_content=body
            )
            
            event = WarmupEvent(
                pair_id=pair.id,
                sender_id=sender.id,
                recipient_id=recipient.id,
                event_type="send",
                status="success"
            )
            db.add(event)
            db.commit()
        except Exception as e:
            event = WarmupEvent(
                pair_id=pair.id,
                sender_id=sender.id,
                recipient_id=recipient.id,
                event_type="send",
                status=f"failed: {str(e)}"
            )
            db.add(event)
            db.commit()
            
        time.sleep(random.uniform(1.0, 5.0)) # Small delay between pairs
        
    db.close()
