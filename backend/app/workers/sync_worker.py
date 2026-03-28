from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.models import Mailbox, Thread, Message
from app.integrations.imap.imap_service import fetch_unread_emails

@celery_app.task
def sync_all_mailboxes():
    db = SessionLocal()
    mailboxes = db.query(Mailbox).filter(Mailbox.is_active == True).all()
    
    for mailbox in mailboxes:
        try:
            emails = fetch_unread_emails(mailbox)
            for email_data in emails:
                thread = db.query(Thread).filter(Thread.mailbox_id == mailbox.id, Thread.subject == email_data['subject']).first()
                if not thread:
                    thread = Thread(mailbox_id=mailbox.id, subject=email_data['subject'], snippet=email_data['text_content'][:100] if email_data['text_content'] else "")
                    db.add(thread)
                    db.commit()
                    db.refresh(thread)
                    
                msg = Message(
                    thread_id=thread.id,
                    message_id=email_data.get('message_id') or "",
                    in_reply_to=email_data.get('in_reply_to'),
                    from_email=email_data.get('from', ''),
                    to_email=mailbox.email,
                    text_content=email_data.get('text_content', ''),
                    html_content=email_data.get('html_content', ''),
                    is_from_me=False
                )
                db.add(msg)
                db.commit()
        except Exception as e:
            print(f"Failed to sync {mailbox.email}: {e}")
            
    db.close()
