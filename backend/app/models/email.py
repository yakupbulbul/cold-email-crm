import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base

class Thread(Base):
    __tablename__ = "threads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mailbox_id = Column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    external_thread_id = Column(String, index=True, nullable=True) # E.g., generic reference header mapping
    
    subject = Column(String, nullable=True)
    contact_email = Column(String, index=True, nullable=True)
    linkage_status = Column(String, default="unlinked", nullable=False)
    participants = Column(JSON, default=list) # List of email addresses
    
    last_message_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    mailbox = relationship("Mailbox")
    campaign = relationship("Campaign")
    contact = relationship("Contact")
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    ai_summary = relationship("AiSummary", back_populates="thread", uselist=False, cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False)
    mailbox_id = Column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    
    direction = Column(String, nullable=False) # "inbound", "outbound"
    
    from_email = Column(String, nullable=False)
    to_emails = Column(JSON, default=list)
    cc_emails = Column(JSON, default=list)
    bcc_emails = Column(JSON, default=list)
    
    subject = Column(Text, nullable=True)
    text_body = Column(Text, nullable=True)
    html_body = Column(Text, nullable=True)
    
    message_id_header = Column(String, index=True, nullable=True)
    imap_uid = Column(String, index=True, nullable=True)
    in_reply_to = Column(String, index=True, nullable=True)
    references_header = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    
    status = Column(String, default="synced") # "synced", "sending", "failed"
    
    sent_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    thread = relationship("Thread", back_populates="messages")


class AiSummary(Base):
    __tablename__ = "ai_summaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    summary = Column(Text, nullable=True)
    intent = Column(String, nullable=True)  # e.g., "interested", "not_interested", "warmup"
    tone = Column(String, nullable=True)
    extracted_entities = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    thread = relationship("Thread", back_populates="ai_summary")
