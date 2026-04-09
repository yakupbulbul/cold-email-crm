from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings
from app.core.database import get_db
from app.integrations.mailcow.client import MailcowClient
from app.models.core import Mailbox, Domain

router = APIRouter()

class MailboxCreate(BaseModel):
    domain_id: str
    email: str
    display_name: str
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_security_mode: Optional[str] = None
    smtp_password: str
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_username: Optional[str] = None
    imap_password: str
    daily_send_limit: int = 50


class MailboxUpdate(BaseModel):
    display_name: str
    daily_send_limit: int = 50
    status: str = "active"
    smtp_security_mode: Optional[str] = None

class MailboxResponse(BaseModel):
    id: str
    domain_id: str
    email: str
    display_name: str
    smtp_host: str
    smtp_port: int
    smtp_security_mode: str
    imap_host: str
    imap_port: int
    warmup_enabled: bool
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
        "smtp_host": mb.smtp_host,
        "smtp_port": mb.smtp_port,
        "smtp_security_mode": mb.smtp_security_mode or ("ssl" if mb.smtp_port == 465 else "starttls"),
        "imap_host": mb.imap_host,
        "imap_port": mb.imap_port,
        "warmup_enabled": mb.warmup_enabled,
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


def resolve_mailbox_connection_defaults(req: MailboxCreate) -> dict:
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
    }


def normalize_smtp_security_mode(value: Optional[str], port: int) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"starttls", "ssl", "plain"}:
        return normalized
    return "ssl" if port == 465 else "starttls"


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
def create_mailbox(req: MailboxCreate, db: Session = Depends(get_db)):
    # Verify domain exists
    domain = db.query(Domain).filter(Domain.id == req.domain_id).first()
    if not domain:
        raise HTTPException(status_code=400, detail="Domain not found")

    validate_mailbox_email_for_domain(req, domain)
    
    existing = db.query(Mailbox).filter(Mailbox.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mailbox email already exists")
    
    connection_defaults = resolve_mailbox_connection_defaults(req)

    remote_mailcow_provisioned = False
    if settings.MAILCOW_ENABLE_MUTATIONS:
        ensure_remote_mailcow_mailbox(req=req, domain=domain)
        remote_mailcow_provisioned = True

    mailbox = Mailbox(
        domain_id=req.domain_id,
        email=req.email.strip().lower(),
        display_name=req.display_name.strip(),
        smtp_host=connection_defaults["smtp_host"],
        smtp_port=connection_defaults["smtp_port"],
        smtp_username=connection_defaults["smtp_username"],
        smtp_password_encrypted=req.smtp_password,  # TODO: encrypt at rest
        smtp_security_mode=connection_defaults["smtp_security_mode"],
        imap_host=connection_defaults["imap_host"],
        imap_port=connection_defaults["imap_port"],
        imap_username=connection_defaults["imap_username"],
        imap_password_encrypted=req.imap_password,  # TODO: encrypt at rest
        daily_send_limit=req.daily_send_limit,
        remote_mailcow_provisioned=remote_mailcow_provisioned,
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)
    return mailbox_to_response(mailbox)

@router.get("/{mailbox_id}")
def get_mailbox(mailbox_id: str, db: Session = Depends(get_db)):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
    return mailbox_to_response(mailbox)


@router.put("/{mailbox_id}")
def update_mailbox(mailbox_id: str, req: MailboxUpdate, db: Session = Depends(get_db)):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    mailbox.display_name = req.display_name.strip()
    mailbox.daily_send_limit = req.daily_send_limit
    mailbox.status = req.status
    mailbox.smtp_security_mode = normalize_smtp_security_mode(req.smtp_security_mode, mailbox.smtp_port)
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)
    return mailbox_to_response(mailbox)


@router.delete("/{mailbox_id}")
def delete_mailbox(mailbox_id: str, db: Session = Depends(get_db)):
    mailbox = db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    db.delete(mailbox)
    db.commit()
    return {"status": "deleted", "id": mailbox_id}


@router.post("/{mailbox_id}/smtp-check")
def check_mailbox_smtp(mailbox_id: str, db: Session = Depends(get_db)):
    from app.services.smtp_service import SMTPManagerService

    service = SMTPManagerService(db)
    return service.check_mailbox_smtp(mailbox_id)
