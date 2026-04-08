import logging

from app.core.database import SessionLocal
from app.models.core import Domain, Mailbox
from app.services.imap_service import IMAPSyncManager
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task
def sync_all_inboxes():
    db = SessionLocal()
    try:
        mailboxes = (
            db.query(Mailbox)
            .join(Domain, Domain.id == Mailbox.domain_id)
            .filter(
                Mailbox.status == "active",
                Domain.mailcow_status == "verified",
            )
            .all()
        )
        manager = IMAPSyncManager(db)
        
        for mb in mailboxes:
            try:
                logger.info(f"Syncing IMAP for {mb.email}")
                manager.sync_mailbox(mb.id)
            except Exception as exc:
                logger.warning(f"Skipping IMAP sync for {mb.email}: {exc}")
            
    except Exception as e:
        logger.error(f"IMAP Sync Worker Error: {e}")
    finally:
        db.close()
