from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.monitoring import JobLog
from app.services.verification_service import EmailVerificationService, verification_result_payload
from app.workers.celery_app import celery_app


@celery_app.task(bind=True)
def run_lead_verification_bulk(self, lead_ids: list[str]):
    db = SessionLocal()
    try:
        job = db.query(JobLog).filter(JobLog.job_id == self.request.id).first()
        if not job:
            job = JobLog(job_id=self.request.id, job_type="lead_verification_bulk", status="queued")
            db.add(job)
            db.commit()
            db.refresh(job)

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.payload_summary = {
            "lead_ids": lead_ids,
            "requested_count": len(lead_ids),
            "processed_count": 0,
            "results": [],
        }
        db.commit()

        service = EmailVerificationService(db)
        results = []
        for lead_id in lead_ids:
            result = service.verify_lead(lead_id)
            results.append(verification_result_payload(result))
            job.payload_summary = {
                **(job.payload_summary or {}),
                "processed_count": len(results),
                "results": results,
            }
            db.add(job)
            db.commit()

        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        job.payload_summary = {
            **(job.payload_summary or {}),
            "processed_count": len(results),
            "results": results,
        }
        db.commit()
    except Exception as exc:
        job = db.query(JobLog).filter(JobLog.job_id == self.request.id).first()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        raise
    finally:
        db.close()
