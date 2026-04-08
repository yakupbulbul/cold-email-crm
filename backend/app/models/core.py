import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base

class Domain(Base):
    __tablename__ = "domains"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="pending")
    mailcow_status = Column(String, default="pending")
    mailcow_detail = Column(String, nullable=True)
    
    # DNS Statuses
    spf_status = Column(String, default="pending")
    dkim_status = Column(String, default="pending")
    dmarc_status = Column(String, default="pending")
    mx_status = Column(String, default="pending")
    dns_results = Column(JSON, nullable=True)
    missing_requirements = Column(JSON, nullable=True)
    verification_summary = Column(JSON, nullable=True)
    verification_error = Column(String, nullable=True)
    last_checked_at = Column(DateTime, nullable=True)
    mailcow_last_checked_at = Column(DateTime, nullable=True)
    dns_last_checked_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mailboxes = relationship("Mailbox", back_populates="domain", cascade="all, delete-orphan")


class Mailbox(Base):
    __tablename__ = "mailboxes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    
    email = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=False)
    
    smtp_host = Column(String, nullable=False)
    smtp_port = Column(Integer, nullable=False)
    smtp_username = Column(String, nullable=False)
    smtp_password_encrypted = Column(String, nullable=False)
    
    imap_host = Column(String, nullable=False)
    imap_port = Column(Integer, nullable=False)
    imap_username = Column(String, nullable=False)
    imap_password_encrypted = Column(String, nullable=False)
    
    warmup_enabled = Column(Boolean, default=False)
    daily_send_limit = Column(Integer, default=50) # Controls maximum capacity
    current_warmup_stage = Column(Integer, default=1)
    
    status = Column(String, default="active")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    domain = relationship("Domain", back_populates="mailboxes")
    
    # Relationships to be injected
    # warmup_sent = relationship(...)
