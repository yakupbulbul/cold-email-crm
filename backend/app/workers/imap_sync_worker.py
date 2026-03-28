from app.workers.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.core import Mailbox
from app.services.imap_service import IMAPSyncManager
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def sync_all_inboxes():
    db = SessionLocal()
    try:
        mailboxes = db.query(Mailbox).filter(Mailbox.status == "active").all()
        manager = IMAPSyncManager(db)
        
        for mb in mailboxes:
            logger.info(f"Syncing IMAP for {mb.email}")
            manager.sync_mailbox(mb.id)
            
    except Exception as e:
        logger.error(f"IMAP Sync Worker Error: {e}")
    finally:
        db.close()
