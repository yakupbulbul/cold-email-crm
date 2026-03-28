from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.health_service import SystemHealthService
from app.models.monitoring import JobLog
from sqlalchemy import func

router = APIRouter()

@router.get("/health")
def get_global_health(db: Session = Depends(get_db)):
    svc = SystemHealthService(db)
    return svc.check_overall_health()

@router.get("/health/db")
def get_db_health(db: Session = Depends(get_db)):
    return SystemHealthService(db).check_db_health()

@router.get("/health/redis")
def get_redis_health(db: Session = Depends(get_db)):
    return SystemHealthService(db).check_redis_health()

@router.get("/health/workers")
def get_worker_health(db: Session = Depends(get_db)):
    return SystemHealthService(db).check_worker_health()

@router.get("/health/smtp")
def get_smtp_health(host: str, port: int = 465, secure: bool = True, db: Session = Depends(get_db)):
    return SystemHealthService(db).check_smtp_health(host, port, secure)

@router.get("/health/imap")
def get_imap_health(host: str, port: int = 993, db: Session = Depends(get_db)):
    return SystemHealthService(db).check_imap_health(host, port)

@router.get("/jobs")
def get_recent_jobs(status: str = "all", db: Session = Depends(get_db)):
    query = db.query(JobLog)
    if status != "all":
        query = query.filter(JobLog.status == status)
    return query.order_by(JobLog.created_at.desc()).limit(100).all()

@router.get("/jobs/failed")
def get_failed_jobs(db: Session = Depends(get_db)):
    return db.query(JobLog).filter(JobLog.status == "failed").order_by(JobLog.created_at.desc()).limit(100).all()

@router.get("/jobs/dead-letter")
def get_dead_letter_jobs(db: Session = Depends(get_db)):
    return db.query(JobLog).filter(JobLog.status == "dead_letter").order_by(JobLog.created_at.desc()).limit(100).all()

@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobLog).filter(JobLog.job_id == job_id).first()
    if not job: raise HTTPException(status_code=404, detail="Job not found")
    job.status = "queued"
    job.retry_count += 1
    db.commit()
    return {"status": "retried", "job_id": job.job_id}

@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobLog).filter(JobLog.job_id == job_id).first()
    if not job: raise HTTPException(status_code=404, detail="Job not found")
    job.status = "cancelled"
    db.commit()
    return {"status": "cancelled"}

@router.get("/jobs/queue-stats")
def get_queue_stats(db: Session = Depends(get_db)):
    stats = db.query(JobLog.status, func.count(JobLog.id)).group_by(JobLog.status).all()
    return {k: v for k, v in stats}
