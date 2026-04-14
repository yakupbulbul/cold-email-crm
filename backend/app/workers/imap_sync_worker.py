import logging
import uuid
from datetime import datetime

from app.core.database import SessionLocal
from app.models.core import Mailbox
from app.models.monitoring import JobLog
from app.services.imap_service import IMAPSyncManager
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task
def sync_all_inboxes():
    db = SessionLocal()
    job = JobLog(
        job_id=str(uuid.uuid4()),
        job_type="imap_sync",
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    try:
        mailboxes = (
            db.query(Mailbox)
            .filter(
                Mailbox.status == "active",
                Mailbox.inbox_sync_enabled.is_(True),
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
        job.status = "completed"
        job.finished_at = datetime.utcnow()
        job.payload_summary = {"mailboxes_processed": len(mailboxes)}
        db.add(job)
        db.commit()
    except Exception as e:
        logger.error(f"IMAP Sync Worker Error: {e}")
        job.status = "failed"
        job.error_message = str(e)
        job.finished_at = datetime.utcnow()
        db.add(job)
        db.commit()
    finally:
        db.close()
