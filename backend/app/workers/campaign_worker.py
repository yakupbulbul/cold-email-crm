import logging
from datetime import datetime

from app.core.database import SessionLocal
from app.models.monitoring import JobLog
from app.services.campaign_service import CampaignService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def run_campaign_cycle(self):
    db = SessionLocal()
    try:
        job = db.query(JobLog).filter(JobLog.job_id == self.request.id).first()
        if not job:
            job = JobLog(job_id=self.request.id, job_type="campaign_cycle", status="queued")
            db.add(job)
            db.commit()
            db.refresh(job)
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        logger.info("Starting Campaign Dispatch Engine cycle")
        service = CampaignService(db)
        service.process_active_campaigns()
        job.status = "completed"
        job.finished_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        logger.error(f"Campaign Worker Error: {e}")
        job = db.query(JobLog).filter(JobLog.job_id == self.request.id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
