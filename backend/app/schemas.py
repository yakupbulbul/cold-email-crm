from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models.models import ContactStatus

class DomainBase(BaseModel):
    name: str

class DomainCreate(DomainBase):
    pass

class DomainResponse(DomainBase):
    id: int
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

class MailboxBase(BaseModel):
    email: EmailStr
    smtp_host: Optional[str] = "mail.example.com"
    smtp_port: Optional[int] = 587
    imap_host: Optional[str] = "mail.example.com"
    imap_port: Optional[int] = 143
    daily_limit: Optional[int] = 50

class MailboxCreate(MailboxBase):
    domain_id: int
    password: str

class MailboxResponse(MailboxBase):
    id: int
    domain_id: int
    is_active: bool
    warmup_enabled: bool
    created_at: datetime
    class Config:
        from_attributes = True

class ContactBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None

class ContactCreate(ContactBase):
    pass

class ContactResponse(ContactBase):
    id: int
    status: ContactStatus
    created_at: datetime
    class Config:
        from_attributes = True

class CampaignBase(BaseModel):
    name: str
    subject_template: str
    body_template: str
    is_active: Optional[bool] = False
    daily_limit: Optional[int] = 50

class CampaignCreate(CampaignBase):
    mailbox_id: int

class CampaignResponse(CampaignBase):
    id: int
    mailbox_id: int
    created_at: datetime
    class Config:
        from_attributes = True
