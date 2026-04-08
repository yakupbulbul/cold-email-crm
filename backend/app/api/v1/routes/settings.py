from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.health_service import SystemHealthService
from app.services.readiness_service import ReadinessService

router = APIRouter()


class SettingsStatusItem(BaseModel):
    status: str
    detail: str | None = None


class SettingsUserSummary(BaseModel):
    email: str
    full_name: str | None = None
    is_admin: bool
    is_active: bool


class SettingsSummaryResponse(BaseModel):
    app_env: str
    project_name: str
    api_base_path: str
    backend_url: str
    frontend_api_path: str
    worker_mode: str
    worker_available: bool
    worker_detail: str | None = None
    readiness_status: str
    safe_mode: bool
    mailcow_mutations_enabled: bool
    mailcow_configured: bool
    mailcow_status: str
    mailcow_reason: str | None = None
    mailcow_detail: str | None = None
    frontend_mailcow_direct_access: bool
    auth_enabled: bool
    session_healthy: bool
    current_user: SettingsUserSummary
    health: dict[str, SettingsStatusItem]


@router.get("/summary", response_model=SettingsSummaryResponse)
def get_settings_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    health_service = SystemHealthService(db)
    readiness_service = ReadinessService(db)

    overall_health = health_service.check_overall_health()
    mailcow_health = health_service.check_mailcow_health()
    readiness = readiness_service.perform_readiness_checks()

    def item(component: dict, *, fallback_detail: str | None = None) -> SettingsStatusItem:
        return SettingsStatusItem(
            status=component.get("status", "unknown"),
            detail=component.get("detail") or component.get("error") or fallback_detail,
        )

    worker_status = overall_health["components"]["workers"]

    return SettingsSummaryResponse(
        app_env=settings.APP_ENV,
        project_name=settings.PROJECT_NAME,
        api_base_path=settings.API_V1_STR,
        backend_url=settings.BACKEND_URL,
        frontend_api_path=settings.NEXT_PUBLIC_API_URL,
        worker_mode="full" if settings.BACKGROUND_WORKERS_ENABLED else "lean",
        worker_available=worker_status.get("status") == "healthy",
        worker_detail=worker_status.get("detail"),
        readiness_status=readiness["status"],
        safe_mode=not settings.MAILCOW_ENABLE_MUTATIONS,
        mailcow_mutations_enabled=settings.MAILCOW_ENABLE_MUTATIONS,
        mailcow_configured=mailcow_health.get("configured", False),
        mailcow_status=mailcow_health.get("status", "unknown"),
        mailcow_reason=mailcow_health.get("reason"),
        mailcow_detail=mailcow_health.get("detail"),
        frontend_mailcow_direct_access=False,
        auth_enabled=True,
        session_healthy=True,
        current_user=SettingsUserSummary(
            email=current_user.email,
            full_name=current_user.full_name,
            is_admin=current_user.is_admin,
            is_active=current_user.is_active,
        ),
        health={
            "backend": SettingsStatusItem(status=overall_health["status"], detail="Backend settings summary endpoint is reachable."),
            "database": item(overall_health["components"]["postgres"]),
            "redis": item(overall_health["components"]["redis"]),
            "workers": item(worker_status),
            "mailcow": item(mailcow_health),
        },
    )
