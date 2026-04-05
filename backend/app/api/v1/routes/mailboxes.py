from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.models.core import Mailbox, Domain

router = APIRouter()

class MailboxCreate(BaseModel):
    domain_id: str
    email: str
    display_name: str
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    imap_host: str
    imap_port: int = 993
    imap_username: str
    imap_password: str
    daily_send_limit: int = 50

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

@router.get("/")
def list_mailboxes(db: Session = Depends(get_db)):
    mailboxes = db.query(Mailbox).all()
    return [mailbox_to_response(mb) for mb in mailboxes]

@router.post("/")
def create_mailbox(req: MailboxCreate, db: Session = Depends(get_db)):
    # Verify domain exists
    domain = db.query(Domain).filter(Domain.id == req.domain_id).first()
    if not domain:
        raise HTTPException(status_code=400, detail="Domain not found")
    
    existing = db.query(Mailbox).filter(Mailbox.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Mailbox email already exists")
    
    mailbox = Mailbox(
        domain_id=req.domain_id,
        email=req.email,
        display_name=req.display_name,
        smtp_host=req.smtp_host,
        smtp_port=req.smtp_port,
        smtp_username=req.smtp_username,
        smtp_password_encrypted=req.smtp_password,  # TODO: encrypt at rest
        imap_host=req.imap_host,
        imap_port=req.imap_port,
        imap_username=req.imap_username,
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
