import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base

class WarmupPair(Base):
    __tablename__ = "warmup_pairs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_mailbox_id = Column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    recipient_mailbox_id = Column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sender = relationship("Mailbox", foreign_keys=[sender_mailbox_id])
    recipient = relationship("Mailbox", foreign_keys=[recipient_mailbox_id])


class WarmupEvent(Base):
    __tablename__ = "warmup_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mailbox_id = Column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    
    event_type = Column(String, nullable=False) # "send", "reply"
    target_email = Column(String, nullable=False)
    
    subject = Column(String, nullable=True)
    body_preview = Column(Text, nullable=True)
    
    status = Column(String, default="pending") # "pending", "success", "failed"
    
    sent_at = Column(DateTime, nullable=True)
    replied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    mailbox = relationship("Mailbox", foreign_keys=[mailbox_id])
