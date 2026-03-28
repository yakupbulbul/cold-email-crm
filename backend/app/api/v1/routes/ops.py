from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.health_service import SystemHealthService

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
