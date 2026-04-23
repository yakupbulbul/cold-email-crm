import logging
from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.monitoring import JobLog
from app.services.warmup_service import WarmupService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def run_warmup_cycle(self, force_send: bool = False):
    db = SessionLocal()
    try:
        job = db.query(JobLog).filter(JobLog.job_id == self.request.id).first()
        if not job:
            job = JobLog(job_id=self.request.id, job_type="warmup_cycle", status="queued")
            db.add(job)
            db.commit()
            db.refresh(job)
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        logger.info("Starting Warm-up Engine cycle")
        service = WarmupService(db)
        result = service.process_all_active_pairs(force_send=force_send)
        job.payload_summary = {
            **(job.payload_summary or {}),
            **result,
        }
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        logger.error(f"Warm-up Worker Error: {e}")
        job = db.query(JobLog).filter(JobLog.job_id == self.request.id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
