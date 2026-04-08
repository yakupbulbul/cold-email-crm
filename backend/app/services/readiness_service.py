from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.health_service import SystemHealthService

class ReadinessService:
    def __init__(self, db: Session):
        self.db = db

    def perform_readiness_checks(self) -> dict:
        health_svc = SystemHealthService(self.db)
        health_stat = health_svc.check_overall_health()

        checks = []

        # Database Check
        pg = health_stat["components"]["postgres"]
        checks.append({
            "category": "Infrastructure",
            "check": "PostgreSQL Connection",
            "status": "pass" if pg["status"] == "healthy" else "fail",
            "detail": "Core datastore is reachable." if pg["status"] == "healthy" else "Database offline."
        })

        # Redis Check
        rd = health_stat["components"]["redis"]
        checks.append({
            "category": "Infrastructure",
            "check": "Redis Backplane",
            "status": "pass" if rd["status"] == "healthy" else "fail",
            "detail": "Queue and cache store is reachable." if rd["status"] == "healthy" else "Redis offline."
        })

        workers = health_stat["components"]["workers"]
        worker_status = "pass"
        worker_detail = "Background workers are running."
        if workers["status"] == "disabled":
            worker_status = "warning"
            worker_detail = workers["detail"]
        elif workers["status"] == "degraded":
            worker_status = "warning"
            worker_detail = "Background workers are only partially healthy."
        elif workers["status"] == "failed":
            worker_status = "fail"
            worker_detail = "Background workers are expected but unavailable."

        checks.append({
            "category": "Background Jobs",
            "check": "Worker and Beat Processes",
            "status": worker_status,
            "detail": worker_detail,
        })

        # Secrets & Keys
        has_secret = bool(settings.SECRET_KEY)
        has_openai = bool(settings.OPENAI_API_KEY)
        mailcow = health_stat["components"]["mailcow"]
        
        checks.append({
            "category": "Security",
            "check": "JWT Secret Key",
            "status": "pass" if has_secret else "fail",
            "detail": "SECRET_KEY is configured for session tokens." if has_secret else "MISSING SECRET_KEY! Auth will fail."
        })

        checks.append({
            "category": "Integrations",
            "check": "OpenAI Credentials",
            "status": "pass" if has_openai else "warning",
            "detail": "AI capabilities are enabled." if has_openai else "OPENAI_API_KEY missing. AI features disabled."
        })

        checks.append({
            "category": "Integrations",
            "check": "Mailcow API Connectivity",
            "status": "pass" if mailcow["status"] == "healthy" else ("warning" if mailcow["status"] in {"degraded", "unknown"} else "fail"),
            "detail": mailcow.get("detail", "Mailcow connectivity check did not return detail."),
        })

        total = len(checks)
        passed = sum(1 for c in checks if c["status"] == "pass")
        warnings = sum(1 for c in checks if c["status"] == "warning")
        if passed == total:
            overall = "ready"
        elif passed + warnings == total and passed >= 3:
            overall = "degraded"
        else:
            overall = "failed"

        return {
            "status": overall,
            "checklist": checks
        }
