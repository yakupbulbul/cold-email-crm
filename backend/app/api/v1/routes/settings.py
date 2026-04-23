from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.command_center_service import record_command_action
from app.services.health_service import SystemHealthService
from app.services.mail_provider_service import MailProviderRegistry
from app.services.provider_settings_service import ProviderSettingsService
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


class ProviderStatusItem(BaseModel):
    enabled: bool
    configured: bool
    status: str
    detail: str | None = None
    reason: str | None = None
    checked_at: str | None = None
    oauth_connection_status: str | None = None
    safe_mode: bool | None = None


class SettingsProvidersUpdateRequest(BaseModel):
    mailcow_enabled: bool | None = None
    google_workspace_enabled: bool | None = None
    default_provider: str | None = None
    allow_existing_disabled_provider_mailboxes: bool | None = None


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
    default_provider: str
    enabled_providers: list[str]
    allow_existing_disabled_provider_mailboxes: bool
    providers: dict[str, ProviderStatusItem]
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
    provider_registry = MailProviderRegistry(db)
    provider_settings = ProviderSettingsService(db).get_or_create()

    try:
        overall_health = health_service.check_overall_health()
    except Exception as exc:
        overall_health = {
            "status": "degraded",
            "components": {
                "postgres": {"status": "unknown", "detail": "Database health could not be determined."},
                "redis": {"status": "unknown", "detail": "Redis health could not be determined."},
                "workers": {"status": "unknown", "detail": "Worker health could not be determined."},
                "mailcow": {"status": "unknown", "detail": "Mailcow health could not be determined."},
                "providers": {},
            },
            "detail": str(exc),
        }

    try:
        mailcow_health = health_service.check_mailcow_health()
    except Exception as exc:
        mailcow_health = {
            "status": provider_settings.mailcow_last_check_status or "unknown",
            "detail": provider_settings.mailcow_last_check_message or "Mailcow health could not be determined.",
            "reason": "mailcow_health_unavailable",
            "configured": bool(settings.MAILCOW_BASE_URL and settings.MAILCOW_API_KEY),
        }

    try:
        readiness = readiness_service.perform_readiness_checks()
    except Exception:
        readiness = {"status": "degraded"}

    try:
        provider_health = provider_registry.provider_health_payload()
    except Exception:
        provider_health = {
            "mailcow": {
                "enabled": provider_settings.mailcow_enabled,
                "configured": bool(settings.MAILCOW_BASE_URL and settings.MAILCOW_API_KEY),
                "status": provider_settings.mailcow_last_check_status or "unknown",
                "detail": provider_settings.mailcow_last_check_message or "Mailcow provider health is currently unavailable.",
                "reason": "provider_health_unavailable",
            },
            "google_workspace": {
                "enabled": provider_settings.google_workspace_enabled,
                "configured": bool(settings.GOOGLE_WORKSPACE_CLIENT_ID and settings.GOOGLE_WORKSPACE_CLIENT_SECRET and settings.GOOGLE_WORKSPACE_REDIRECT_URI),
                "status": provider_settings.google_workspace_last_check_status or "unknown",
                "detail": provider_settings.google_workspace_last_check_message or "Google Workspace provider health is currently unavailable.",
                "reason": "provider_health_unavailable",
            },
        }

    provider_settings.mailcow_last_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
    provider_settings.mailcow_last_check_status = provider_health["mailcow"]["status"]
    provider_settings.mailcow_last_check_message = provider_health["mailcow"].get("detail")
    provider_settings.google_workspace_last_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
    provider_settings.google_workspace_last_check_status = provider_health["google_workspace"]["status"]
    provider_settings.google_workspace_last_check_message = provider_health["google_workspace"].get("detail")
    db.add(provider_settings)
    db.commit()
    db.refresh(provider_settings)

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
        default_provider=provider_settings.default_provider,
        enabled_providers=[key for key, enabled in provider_registry.get_enabled_provider_map().items() if enabled],
        allow_existing_disabled_provider_mailboxes=provider_settings.allow_existing_disabled_provider_mailboxes,
        providers={
            "mailcow": ProviderStatusItem(
                enabled=provider_settings.mailcow_enabled,
                configured=provider_health["mailcow"].get("configured", False),
                status=provider_health["mailcow"].get("status", "unknown"),
                detail=provider_health["mailcow"].get("detail"),
                reason=provider_health["mailcow"].get("reason"),
                checked_at=provider_settings.mailcow_last_checked_at.isoformat() if provider_settings.mailcow_last_checked_at else None,
                safe_mode=not settings.MAILCOW_ENABLE_MUTATIONS,
            ),
            "google_workspace": ProviderStatusItem(
                enabled=provider_settings.google_workspace_enabled,
                configured=provider_health["google_workspace"].get("configured", False),
                status=provider_health["google_workspace"].get("status", "unknown"),
                detail=provider_health["google_workspace"].get("detail"),
                reason=provider_health["google_workspace"].get("reason"),
                checked_at=provider_settings.google_workspace_last_checked_at.isoformat() if provider_settings.google_workspace_last_checked_at else None,
                oauth_connection_status="connected" if provider_health["google_workspace"].get("configured") else "not_connected",
            ),
        },
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


@router.patch("/providers", response_model=SettingsSummaryResponse)
def update_provider_settings(
    req: SettingsProvidersUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can update provider settings.")
    if req.default_provider and req.default_provider not in {"mailcow", "google_workspace"}:
        raise HTTPException(status_code=422, detail="default_provider must be mailcow or google_workspace.")
    ProviderSettingsService(db).update(
        mailcow_enabled=req.mailcow_enabled,
        google_workspace_enabled=req.google_workspace_enabled,
        default_provider=req.default_provider,
        allow_existing_disabled_provider_mailboxes=req.allow_existing_disabled_provider_mailboxes,
    )
    record_command_action(
        db,
        action_type="provider_settings_updated",
        source="settings",
        result="success",
        message="Provider settings updated.",
        actor=current_user,
        metadata={
            "mailcow_enabled": req.mailcow_enabled,
            "google_workspace_enabled": req.google_workspace_enabled,
            "default_provider": req.default_provider,
            "allow_existing_disabled_provider_mailboxes": req.allow_existing_disabled_provider_mailboxes,
        },
    )
    return get_settings_summary(db=db, current_user=current_user)
