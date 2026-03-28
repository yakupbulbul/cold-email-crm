import logging
import subprocess
import os
import smtplib
import imaplib
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SystemHealthService:
    def __init__(self, db: Session):
        self.db = db

    def check_db_health(self) -> Dict[str, Any]:
        try:
            self.db.execute(text("SELECT 1"))
            return {"status": "healthy", "service": "postgres", "latency_ms": 1} # simplified latency tracking
        except Exception as e:
            logger.error(f"DB Health Check Failed: {e}")
            return {"status": "failed", "service": "postgres", "error": str(e)}

    def check_redis_health(self) -> Dict[str, Any]:
        try:
            import redis
            redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
            r = redis.Redis.from_url(redis_url, socket_timeout=2)
            r.ping()
            return {"status": "healthy", "service": "redis"}
        except Exception as e:
            logger.error(f"Redis Health Check Failed: {e}")
            return {"status": "failed", "service": "redis", "error": str(e)}

    def check_worker_health(self) -> Dict[str, Any]:
        from app.models.monitoring import WorkerHeartbeat
        from datetime import datetime, timedelta
        
        threshold = datetime.utcnow() - timedelta(minutes=5)
        active_workers = self.db.query(WorkerHeartbeat).filter(WorkerHeartbeat.last_seen_at >= threshold).count()
        total_workers = self.db.query(WorkerHeartbeat).count()
        
        status = "healthy"
        if active_workers == 0 and total_workers > 0:
            status = "failed"
        elif active_workers < total_workers:
            status = "degraded"
            
        return {
            "status": status,
            "service": "workers",
            "active_count": active_workers,
            "total_registered": total_workers
        }

    def check_smtp_health(self, host: str, port: int, secure: bool = True) -> Dict[str, Any]:
        try:
            server = smtplib.SMTP_SSL(host, port, timeout=5) if secure else smtplib.SMTP(host, port, timeout=5)
            server.ehlo()
            server.quit()
            return {"status": "healthy", "service": f"smtp_{host}"}
        except Exception as e:
            logger.error(f"SMTP Check Failed for {host}: {e}")
            return {"status": "failed", "service": f"smtp_{host}", "error": str(e)}

    def check_imap_health(self, host: str, port: int) -> Dict[str, Any]:
        try:
            server = imaplib.IMAP4_SSL(host, port)
            server.logout()
            return {"status": "healthy", "service": f"imap_{host}"}
        except Exception as e:
            logger.error(f"IMAP Check Failed for {host}: {e}")
            return {"status": "failed", "service": f"imap_{host}", "error": str(e)}

    def check_overall_health(self) -> Dict[str, Any]:
        db_stat = self.check_db_health()
        redis_stat = self.check_redis_health()
        worker_stat = self.check_worker_health()
        
        # Generic SMTP assumption pointing mapping Mailcow
        # For precise check we read exact mailbox domains but global check assumes "mailcow" container existence
        smtp_stat = {"status": "unknown", "service": "global_smtp"}
        
        is_all_healthy = all(x["status"] == "healthy" for x in [db_stat, redis_stat])
        is_any_failed = any(x["status"] == "failed" for x in [db_stat, redis_stat, worker_stat])
        
        overall = "healthy"
        if is_any_failed:
            overall = "failed"
        elif not is_all_healthy or worker_stat["status"] == "degraded":
            overall = "degraded"
            
        return {
            "status": overall,
            "components": {
                "postgres": db_stat,
                "redis": redis_stat,
                "workers": worker_stat,
                "smtp_engine": smtp_stat
            }
        }
