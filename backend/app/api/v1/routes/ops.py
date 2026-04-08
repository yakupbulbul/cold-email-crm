from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.health_service import SystemHealthService
from app.models.monitoring import JobLog, SystemAlert, AuditLog
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

@router.get("/health/mailcow")
def get_mailcow_health(db: Session = Depends(get_db)):
    return SystemHealthService(db).check_mailcow_health()

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

# Alerts
@router.get("/alerts")
def get_active_alerts(unacknowledged: bool = False, db: Session = Depends(get_db)):
    q = db.query(SystemAlert).filter(SystemAlert.is_active == True)
    if unacknowledged:
        q = q.filter(SystemAlert.is_acknowledged == False)
    return q.order_by(SystemAlert.created_at.desc()).all()

@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
    if alert:
        alert.is_acknowledged = True
        import datetime
        alert.acknowledged_at = datetime.datetime.utcnow()
        db.commit()
    return {"status": "acknowledged"}

@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, db: Session = Depends(get_db)):
    alert = db.query(SystemAlert).filter(SystemAlert.id == alert_id).first()
    if alert:
        alert.is_active = False
        db.commit()
    return {"status": "resolved"}

# Audit Logs
@router.get("/audit-logs")
def get_audit_logs(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()

# Readiness
@router.get("/readiness")
def get_readiness_checklist(db: Session = Depends(get_db)):
    from app.services.readiness_service import ReadinessService
    return ReadinessService(db).perform_readiness_checks()
