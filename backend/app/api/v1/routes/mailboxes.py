from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from app.core.database import get_db
from app.models.core import Mailbox, Domain

router = APIRouter()

class MailboxCreate(BaseModel):
    domain_id: str
    email: str
    display_name: str
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
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

class MailboxResponse(BaseModel):
    id: str
    domain_id: str
    email: str
    display_name: str
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
    warmup_enabled: bool
    daily_send_limit: int
    current_warmup_stage: int
    status: str
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
        "imap_host": mb.imap_host,
        "imap_port": mb.imap_port,
        "warmup_enabled": mb.warmup_enabled,
        "daily_send_limit": mb.daily_send_limit,
        "current_warmup_stage": mb.current_warmup_stage,
        "status": mb.status,
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
        "imap_host": imap_host,
        "imap_port": req.imap_port or settings.MAILCOW_IMAP_PORT,
        "imap_username": req.imap_username or req.email,
    }

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
    
    existing = db.query(Mailbox).filter(Mailbox.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mailbox email already exists")
    
    connection_defaults = resolve_mailbox_connection_defaults(req)

    # Safe mode keeps mailbox creation local-only unless a future explicit
    # Mailcow provisioning path is enabled server-side.
    mailbox = Mailbox(
        domain_id=req.domain_id,
        email=req.email,
        display_name=req.display_name,
        smtp_host=connection_defaults["smtp_host"],
        smtp_port=connection_defaults["smtp_port"],
        smtp_username=connection_defaults["smtp_username"],
        smtp_password_encrypted=req.smtp_password,  # TODO: encrypt at rest
        imap_host=connection_defaults["imap_host"],
        imap_port=connection_defaults["imap_port"],
        imap_username=connection_defaults["imap_username"],
        imap_password_encrypted=req.imap_password,  # TODO: encrypt at rest
        daily_send_limit=req.daily_send_limit,
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
