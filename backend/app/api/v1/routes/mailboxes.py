from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.integrations.mailcow.client import MailcowClient
from app.models.core import Mailbox, Domain
from app.models.user import User
from app.schemas.warmup import WarmupMailboxToggleRequest
from app.services.command_center_service import record_command_action
from app.services.google_oauth_service import GoogleOAuthError, GoogleWorkspaceOAuthService
from app.services.mail_provider_service import MailProviderRegistry, ProviderUnavailableError
from app.services.provider_settings_service import ProviderSettingsService
from app.services.warmup_service import WarmupService

router = APIRouter()

class MailboxCreate(BaseModel):
    domain_id: str
    email: str
    display_name: str
    provider_type: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_security_mode: Optional[str] = None
    smtp_password: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_username: Optional[str] = None
    imap_password: Optional[str] = None
    imap_security_mode: Optional[str] = None
    oauth_enabled: Optional[bool] = None
    daily_send_limit: int = 50


class MailboxUpdate(BaseModel):
    display_name: str
    daily_send_limit: int = 50
    status: str = "active"
    smtp_security_mode: Optional[str] = None
    provider_type: Optional[str] = None
    oauth_enabled: Optional[bool] = None

class MailboxResponse(BaseModel):
    id: str
    domain_id: str
    email: str
    display_name: str
    provider_type: str
    provider_status: str
    provider_mailbox_id: Optional[str] = None
    provider_domain_id: Optional[str] = None
    provider_config_status: str
    last_provider_check_at: Optional[str] = None
    last_provider_check_status: Optional[str] = None
    last_provider_check_message: Optional[str] = None
    smtp_host: str
    smtp_port: int
    smtp_security_mode: str
    imap_host: str
    imap_port: int
    imap_security_mode: str
    oauth_enabled: bool
    oauth_provider: Optional[str] = None
    oauth_connection_status: Optional[str] = None
    oauth_last_checked_at: Optional[str] = None
    oauth_last_error: Optional[str] = None
    oauth_last_refreshed_at: Optional[str] = None
    oauth_token_expires_at: Optional[str] = None
    external_account_email: Optional[str] = None
    warmup_enabled: bool
    warmup_status: Optional[str] = None
    warmup_last_checked_at: Optional[str] = None
    warmup_last_result: Optional[str] = None
    warmup_block_reason: Optional[str] = None
    inbox_sync_enabled: bool
    inbox_sync_status: Optional[str] = None
    inbox_last_synced_at: Optional[str] = None
    inbox_last_success_at: Optional[str] = None
    inbox_last_error: Optional[str] = None
    daily_send_limit: int
    current_warmup_stage: int
    status: str
    remote_mailcow_provisioned: bool
    provisioning_mode: str
    smtp_last_checked_at: Optional[str] = None
    smtp_last_check_status: Optional[str] = None
    smtp_last_check_category: Optional[str] = None
    smtp_last_check_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

def mailbox_to_response(mb: Mailbox) -> dict:
    """Convert a Mailbox ORM object to a safe response dict (no credentials leaked)."""
    return {
        "id": str(mb.id),
        "domain_id": str(mb.domain_id),
        "email": mb.email,
        "display_name": mb.display_name,
        "provider_type": mb.provider_type or "mailcow",
        "provider_status": mb.provider_status or "active",
        "provider_mailbox_id": mb.provider_mailbox_id,
        "provider_domain_id": mb.provider_domain_id,
        "provider_config_status": mb.provider_config_status or "configured",
        "last_provider_check_at": mb.last_provider_check_at.isoformat() if mb.last_provider_check_at else None,
        "last_provider_check_status": mb.last_provider_check_status,
        "last_provider_check_message": mb.last_provider_check_message,
        "smtp_host": mb.smtp_host,
        "smtp_port": mb.smtp_port,
        "smtp_security_mode": mb.smtp_security_mode or ("ssl" if mb.smtp_port == 465 else "starttls"),
        "imap_host": mb.imap_host,
        "imap_port": mb.imap_port,
        "imap_security_mode": mb.imap_security_mode or ("plain" if mb.imap_port == 143 else "ssl"),
        "oauth_enabled": mb.oauth_enabled,
        "oauth_provider": mb.oauth_provider,
        "oauth_connection_status": mb.oauth_connection_status,
        "oauth_last_checked_at": mb.oauth_last_checked_at.isoformat() if mb.oauth_last_checked_at else None,
        "oauth_last_error": mb.oauth_last_error,
        "oauth_last_refreshed_at": mb.oauth_token.last_refreshed_at.isoformat() if mb.oauth_token and mb.oauth_token.last_refreshed_at else None,
        "oauth_token_expires_at": mb.oauth_token.token_expiry.isoformat() if mb.oauth_token and mb.oauth_token.token_expiry else None,
        "external_account_email": mb.oauth_token.external_account_email if mb.oauth_token else None,
        "warmup_enabled": mb.warmup_enabled,
        "warmup_status": mb.warmup_status,
        "warmup_last_checked_at": mb.warmup_last_checked_at.isoformat() if mb.warmup_last_checked_at else None,
        "warmup_last_result": mb.warmup_last_result,
        "warmup_block_reason": mb.warmup_block_reason,
        "inbox_sync_enabled": mb.inbox_sync_enabled,
        "inbox_sync_status": mb.inbox_sync_status,
        "inbox_last_synced_at": mb.inbox_last_synced_at.isoformat() if mb.inbox_last_synced_at else None,
        "inbox_last_success_at": mb.inbox_last_success_at.isoformat() if mb.inbox_last_success_at else None,
        "inbox_last_error": mb.inbox_last_error,
        "daily_send_limit": mb.daily_send_limit,
        "current_warmup_stage": mb.current_warmup_stage,
        "status": mb.status,
        "remote_mailcow_provisioned": mb.remote_mailcow_provisioned,
        "provisioning_mode": "mailcow_synced" if mb.remote_mailcow_provisioned else "local_only",
        "smtp_last_checked_at": mb.smtp_last_checked_at.isoformat() if mb.smtp_last_checked_at else None,
        "smtp_last_check_status": mb.smtp_last_check_status,
        "smtp_last_check_category": mb.smtp_last_check_category,
        "smtp_last_check_message": mb.smtp_last_check_message,
        "created_at": str(mb.created_at) if mb.created_at else None,
        "updated_at": str(mb.updated_at) if mb.updated_at else None,
}


def resolve_mailbox_connection_defaults(req: MailboxCreate, provider_type: str) -> dict:
    if provider_type == "google_workspace":
        smtp_host = req.smtp_host or settings.GOOGLE_WORKSPACE_SMTP_HOST
        imap_host = req.imap_host or settings.GOOGLE_WORKSPACE_IMAP_HOST
        smtp_port = req.smtp_port or settings.GOOGLE_WORKSPACE_SMTP_PORT
        imap_port = req.imap_port or settings.GOOGLE_WORKSPACE_IMAP_PORT
        smtp_security_mode = normalize_smtp_security_mode(req.smtp_security_mode, smtp_port)
        imap_security_mode = normalize_imap_security_mode(req.imap_security_mode, imap_port)
        return {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_username": req.smtp_username or req.email,
            "smtp_security_mode": smtp_security_mode,
            "imap_host": imap_host,
            "imap_port": imap_port,
            "imap_username": req.imap_username or req.email,
            "imap_security_mode": imap_security_mode,
        }

    smtp_host = req.smtp_host or settings.MAILCOW_SMTP_HOST
    imap_host = req.imap_host or settings.MAILCOW_IMAP_HOST
    if not smtp_host or not imap_host:
        raise HTTPException(
            status_code=400,
            detail="smtp_host and imap_host are required unless MAILCOW_SMTP_HOST and MAILCOW_IMAP_HOST are configured server-side.",
        )

    return {
        "smtp_host": smtp_host,
        "smtp_port": req.smtp_port or settings.MAILCOW_SMTP_PORT,
        "smtp_username": req.smtp_username or req.email,
        "smtp_security_mode": normalize_smtp_security_mode(req.smtp_security_mode, req.smtp_port or settings.MAILCOW_SMTP_PORT),
        "imap_host": imap_host,
        "imap_port": req.imap_port or settings.MAILCOW_IMAP_PORT,
        "imap_username": req.imap_username or req.email,
        "imap_security_mode": normalize_imap_security_mode(req.imap_security_mode, req.imap_port or settings.MAILCOW_IMAP_PORT),
    }


def normalize_smtp_security_mode(value: Optional[str], port: int) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"starttls", "ssl", "plain"}:
        return normalized
    return "ssl" if port == 465 else "starttls"


def normalize_imap_security_mode(value: Optional[str], port: int) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"ssl", "starttls", "plain"}:
        return normalized
    return "plain" if port == 143 else "ssl"


def validate_mailbox_email_for_domain(req: MailboxCreate, domain: Domain) -> None:
    local_part, separator, email_domain = req.email.strip().lower().partition("@")
    if not separator or not local_part or email_domain != domain.name.lower():
        raise HTTPException(
            status_code=400,
            detail="Mailbox email must belong to the selected domain.",
        )


def ensure_remote_mailcow_mailbox(
    *,
    req: MailboxCreate,
    domain: Domain,
) -> None:
    client = MailcowClient()
    if not client.configured:
        raise HTTPException(
            status_code=424,
            detail="Mailcow mutations are enabled but the Mailcow API is not configured.",
        )

    domain_result = client.lookup_domain(domain.name)
    if domain_result.status == "not_found":
        raise HTTPException(status_code=409, detail="Selected domain does not exist in remote Mailcow.")
    if domain_result.status == "unauthorized":
        raise HTTPException(status_code=502, detail="Mailcow rejected the configured credentials.")
    if domain_result.status == "unreachable":
        raise HTTPException(status_code=502, detail="Mailcow is unreachable from the backend environment.")
    if domain_result.status not in {"verified"}:
        raise HTTPException(status_code=502, detail="Mailcow returned an unexpected domain verification response.")

    provision_result = client.create_mailbox(
        email=req.email.strip().lower(),
        display_name=req.display_name.strip(),
        password=req.smtp_password,
    )
    if provision_result.created:
        return
    if provision_result.reason == "mailbox_exists":
        raise HTTPException(status_code=409, detail="Mailbox already exists in remote Mailcow.")
    if provision_result.reason == "domain_missing":
        raise HTTPException(status_code=409, detail="Selected domain does not exist in remote Mailcow.")
    if provision_result.reason == "unauthorized":
        raise HTTPException(status_code=502, detail="Mailcow rejected the configured credentials.")
    if provision_result.reason == "unreachable":
        raise HTTPException(status_code=502, detail="Mailcow is unreachable from the backend environment.")
    if provision_result.reason == "misconfigured":
        raise HTTPException(status_code=424, detail="Mailcow mutations are enabled but the Mailcow API is not configured.")
    raise HTTPException(status_code=502, detail="Mailcow returned an unexpected mailbox provisioning response.")

@router.get("/")
@router.get("")  # Handle both /mailboxes and /mailboxes/ without redirect
def list_mailboxes(db: Session = Depends(get_db)):
    mailboxes = db.query(Mailbox).all()
    return [mailbox_to_response(mb) for mb in mailboxes]

@router.post("/")
@router.post("")  # Handle both /mailboxes and /mailboxes/ without redirect
def create_mailbox(req: MailboxCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    provider_type = (req.provider_type or ProviderSettingsService(db).get_or_create().default_provider or "mailcow").strip().lower()
    registry = MailProviderRegistry(db)
    registry.ensure_provider_allowed(provider_type)

    # Verify domain exists
    domain = db.query(Domain).filter(Domain.id == req.domain_id).first()
    if not domain:
        raise HTTPException(status_code=400, detail="Domain not found")

    validate_mailbox_email_for_domain(req, domain)
    
    existing = db.query(Mailbox).filter(Mailbox.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mailbox email already exists")
    
    connection_defaults = resolve_mailbox_connection_defaults(req, provider_type)
    if provider_type == "mailcow" and (not req.smtp_password or not req.imap_password):
        raise HTTPException(status_code=422, detail="smtp_password and imap_password are required for Mailcow mailboxes.")

    remote_mailcow_provisioned = False
    if provider_type == "mailcow" and settings.MAILCOW_ENABLE_MUTATIONS:
        ensure_remote_mailcow_mailbox(req=req, domain=domain)
        remote_mailcow_provisioned = True

    mailbox = Mailbox(
        domain_id=req.domain_id,
        email=req.email.strip().lower(),
        display_name=req.display_name.strip(),
        provider_type=provider_type,
        provider_status="active",
        provider_domain_id=str(domain.id),
        provider_config_status="configured",
        smtp_host=connection_defaults["smtp_host"],
        smtp_port=connection_defaults["smtp_port"],
        smtp_username=connection_defaults["smtp_username"],
        smtp_password_encrypted=req.smtp_password or "",
        smtp_security_mode=connection_defaults["smtp_security_mode"],
        imap_host=connection_defaults["imap_host"],
        imap_port=connection_defaults["imap_port"],
        imap_username=connection_defaults["imap_username"],
        imap_password_encrypted=req.imap_password or "",
        imap_security_mode=connection_defaults["imap_security_mode"],
        oauth_enabled=bool(req.oauth_enabled) if provider_type == "google_workspace" else False,
        oauth_provider="google_workspace" if provider_type == "google_workspace" else None,
        oauth_connection_status="not_connected" if provider_type == "google_workspace" else None,
        daily_send_limit=req.daily_send_limit,
        remote_mailcow_provisioned=remote_mailcow_provisioned,
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)
    record_command_action(
        db,
        action_type="mailbox_created",
        source="mailboxes",
        result="success",
        message=f"Mailbox created: {mailbox.email}",
        related_entity_type="mailbox",
        related_entity_id=mailbox.id,
        actor=current_user,
        metadata={"provider_type": mailbox.provider_type, "domain_id": str(mailbox.domain_id)},
    )
    return mailbox_to_response(mailbox)

@router.get("/{mailbox_id}")
def get_mailbox(mailbox_id: str, db: Session = Depends(get_db)):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    return mailbox_to_response(mailbox)


@router.put("/{mailbox_id}")
def update_mailbox(mailbox_id: str, req: MailboxUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    if req.provider_type:
        registry = MailProviderRegistry(db)
        registry.ensure_provider_allowed(req.provider_type, mailbox=mailbox)
        mailbox.provider_type = req.provider_type.strip().lower()
        if mailbox.provider_type == "google_workspace":
            mailbox.oauth_enabled = bool(req.oauth_enabled) if req.oauth_enabled is not None else mailbox.oauth_enabled
            mailbox.oauth_provider = "google_workspace"
            if not mailbox.smtp_host:
                mailbox.smtp_host = settings.GOOGLE_WORKSPACE_SMTP_HOST
                mailbox.smtp_port = settings.GOOGLE_WORKSPACE_SMTP_PORT
            if not mailbox.imap_host:
                mailbox.imap_host = settings.GOOGLE_WORKSPACE_IMAP_HOST
                mailbox.imap_port = settings.GOOGLE_WORKSPACE_IMAP_PORT

    mailbox.display_name = req.display_name.strip()
    mailbox.daily_send_limit = req.daily_send_limit
    mailbox.status = req.status
    mailbox.smtp_security_mode = normalize_smtp_security_mode(req.smtp_security_mode, mailbox.smtp_port)
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)
    record_command_action(
        db,
        action_type="mailbox_updated",
        source="mailboxes",
        result="success",
        message=f"Mailbox updated: {mailbox.email}",
        related_entity_type="mailbox",
        related_entity_id=mailbox.id,
        actor=current_user,
        metadata={"provider_type": mailbox.provider_type, "status": mailbox.status},
    )
    return mailbox_to_response(mailbox)


@router.delete("/{mailbox_id}")
def delete_mailbox(mailbox_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    mailbox_email = mailbox.email
    db.delete(mailbox)
    db.commit()
    record_command_action(
        db,
        action_type="mailbox_deleted",
        source="mailboxes",
        result="success",
        message=f"Mailbox deleted: {mailbox_email}",
        related_entity_type="mailbox",
        related_entity_id=mailbox_id,
        actor=current_user,
    )
    return {"status": "deleted", "id": mailbox_id}


@router.post("/{mailbox_id}/smtp-check")
def check_mailbox_smtp(mailbox_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    from app.services.smtp_service import SMTPManagerService

    service = SMTPManagerService(db)
    result = service.check_mailbox_smtp(mailbox_id)
    record_command_action(
        db,
        action_type="mailbox_smtp_check",
        source="mailboxes",
        result="success" if result.get("status") == "healthy" else "failed",
        message=result.get("message") or "Mailbox SMTP check completed.",
        related_entity_type="mailbox",
        related_entity_id=mailbox_id,
        actor=current_user,
        metadata={"status": result.get("status"), "category": result.get("category")},
    )
    return result


@router.post("/{mailbox_id}/provider-check")
def check_mailbox_provider(mailbox_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    registry = MailProviderRegistry(db)
    def mark_oauth_failure(exc: GoogleOAuthError):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        status_by_category = {
            "needs_reauth": "not_connected",
            "oauth_refresh_failed": "expired",
            "oauth_misconfigured": "error",
        }
        mailbox.oauth_connection_status = status_by_category.get(exc.category, "error")
        mailbox.oauth_last_checked_at = now
        mailbox.oauth_last_error = exc.message
        mailbox.last_provider_check_at = now
        mailbox.last_provider_check_status = "failed"
        mailbox.last_provider_check_message = exc.message
        db.add(mailbox)
        db.commit()

    try:
        provider = registry.resolve_mailbox_provider(mailbox)
        smtp_result = provider.diagnose_smtp(mailbox)
        imap_result = provider.diagnose_imap(mailbox)
    except ProviderUnavailableError as exc:
        record_command_action(
            db,
            action_type="mailbox_provider_check",
            source="mailboxes",
            result="failed",
            message=exc.message,
            related_entity_type="mailbox",
            related_entity_id=mailbox_id,
            actor=current_user,
            metadata={"category": exc.category, "provider_type": mailbox.provider_type},
        )
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, "category": exc.category}) from exc
    except GoogleOAuthError as exc:
        mark_oauth_failure(exc)
        record_command_action(
            db,
            action_type="mailbox_provider_check",
            source="mailboxes",
            result="failed",
            message=exc.message,
            related_entity_type="mailbox",
            related_entity_id=mailbox_id,
            actor=current_user,
            metadata={"category": exc.category, "provider_type": mailbox.provider_type},
        )
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, "category": exc.category}) from exc
    except Exception as exc:
        record_command_action(
            db,
            action_type="mailbox_provider_check",
            source="mailboxes",
            result="failed",
            message=str(exc),
            related_entity_type="mailbox",
            related_entity_id=mailbox_id,
            actor=current_user,
            metadata={"category": "provider_check_failed", "provider_type": mailbox.provider_type},
        )
        raise HTTPException(status_code=502, detail={"message": str(exc), "category": "provider_check_failed"}) from exc

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    mailbox.last_provider_check_at = now
    mailbox.smtp_last_checked_at = now
    mailbox.oauth_last_checked_at = now
    if (mailbox.provider_type or "mailcow") == "google_workspace":
        mailbox.oauth_connection_status = "connected"
        mailbox.oauth_last_error = None
    mailbox.last_provider_check_status = "healthy" if smtp_result.status == "healthy" and imap_result.status == "healthy" else "failed"
    mailbox.last_provider_check_message = (
        "Provider diagnostics completed."
        if mailbox.last_provider_check_status == "healthy"
        else f"Provider diagnostics failed. SMTP: {smtp_result.message} IMAP: {imap_result.message}"
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)
    response = {
        "provider_type": mailbox.provider_type,
        "status": mailbox.last_provider_check_status,
        "smtp": {
            "status": smtp_result.status,
            "category": smtp_result.category,
            "message": smtp_result.message,
        },
        "imap": {
            "status": imap_result.status,
            "category": imap_result.category,
            "message": imap_result.message,
        },
        "oauth": GoogleWorkspaceOAuthService(db).safe_status(mailbox) if (mailbox.provider_type or "mailcow") == "google_workspace" else None,
    }
    record_command_action(
        db,
        action_type="mailbox_provider_check",
        source="mailboxes",
        result="success" if mailbox.last_provider_check_status == "healthy" else "failed",
        message=mailbox.last_provider_check_message or "Provider diagnostics completed.",
        related_entity_type="mailbox",
        related_entity_id=mailbox.id,
        actor=current_user,
        metadata={"provider_type": mailbox.provider_type, "status": mailbox.last_provider_check_status},
    )
    return response


@router.get("/{mailbox_id}/oauth-status")
def get_mailbox_oauth_status(mailbox_id: str, db: Session = Depends(get_db)):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    return GoogleWorkspaceOAuthService(db).safe_status(mailbox)


@router.post("/{mailbox_id}/oauth/start")
def start_mailbox_oauth(mailbox_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    if (mailbox.provider_type or "mailcow") != "google_workspace":
        raise HTTPException(status_code=409, detail="OAuth is only available for Google Workspace mailboxes.")
    try:
        authorization_url = GoogleWorkspaceOAuthService(db).build_authorization_url(mailbox)
    except GoogleOAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, "category": exc.category}) from exc
    record_command_action(
        db,
        action_type="google_oauth_started",
        source="mailboxes",
        result="success",
        message=f"Google Workspace OAuth connection started for {mailbox.email}.",
        related_entity_type="mailbox",
        related_entity_id=mailbox.id,
        actor=current_user,
        metadata={"provider_type": mailbox.provider_type},
    )
    return {"status": "ready", "authorization_url": authorization_url}


@router.post("/{mailbox_id}/google-workspace/connect")
def connect_google_workspace_mailbox(
    mailbox_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return start_mailbox_oauth(mailbox_id=mailbox_id, db=db, current_user=current_user)


@router.post("/{mailbox_id}/oauth/disconnect")
def disconnect_mailbox_oauth(mailbox_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    if (mailbox.provider_type or "mailcow") != "google_workspace":
        raise HTTPException(status_code=409, detail="OAuth is only available for Google Workspace mailboxes.")
    try:
        refreshed = GoogleWorkspaceOAuthService(db).disconnect(mailbox)
    except GoogleOAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, "category": exc.category}) from exc
    record_command_action(
        db,
        action_type="google_oauth_disconnected",
        source="mailboxes",
        result="success",
        message=f"Google Workspace OAuth disconnected for {refreshed.email}.",
        related_entity_type="mailbox",
        related_entity_id=refreshed.id,
        actor=current_user,
        metadata={"provider_type": refreshed.provider_type},
    )
    return mailbox_to_response(refreshed)


@router.post("/{mailbox_id}/google-workspace/disconnect")
def disconnect_google_workspace_mailbox(
    mailbox_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return disconnect_mailbox_oauth(mailbox_id=mailbox_id, db=db, current_user=current_user)


@router.patch("/{mailbox_id}/warmup")
def update_mailbox_warmup(
    mailbox_id: str,
    req: WarmupMailboxToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = WarmupService(db)
    try:
        mailbox = service.set_mailbox_participation(mailbox_id, req.warmup_enabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    record_command_action(
        db,
        action_type="mailbox_warmup_toggled",
        source="mailboxes",
        result="success",
        message=f"Warm-up {'enabled' if req.warmup_enabled else 'disabled'} for {mailbox.email}.",
        related_entity_type="mailbox",
        related_entity_id=mailbox.id,
        actor=current_user,
        metadata={"warmup_enabled": req.warmup_enabled},
    )
    return mailbox_to_response(mailbox)
