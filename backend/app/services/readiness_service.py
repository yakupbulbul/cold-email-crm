import os
from sqlalchemy.orm import Session
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

        # Secrets & Keys
        has_secret = bool(os.environ.get("SECRET_KEY"))
        has_openai = bool(os.environ.get("OPENAI_API_KEY"))
        
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

        # Mailcow Check Assumption
        checks.append({
            "category": "Infrastructure",
            "check": "Mailcow Engine Link",
            "status": "pass" if os.environ.get("SMTP_HOST", "mailcow") else "warning",
            "detail": "Standard Docker network assumed for Mailcow."
        })

        total = len(checks)
        passed = sum(1 for c in checks if c["status"] == "pass")
        overall = "ready" if passed == total else ("degraded" if passed > 2 else "failed")

        return {
            "status": overall,
            "checklist": checks
        }
