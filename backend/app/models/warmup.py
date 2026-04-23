import uuid
from datetime import datetime, timezone
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
    state = Column(String, default="active", nullable=False)
    last_sent_at = Column(DateTime, nullable=True)
    next_scheduled_at = Column(DateTime, nullable=True)
    last_result = Column(String, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationships
    sender = relationship("Mailbox", foreign_keys=[sender_mailbox_id])
    recipient = relationship("Mailbox", foreign_keys=[recipient_mailbox_id])


class WarmupEvent(Base):
    __tablename__ = "warmup_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mailbox_id = Column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False)
    pair_id = Column(UUID(as_uuid=True), ForeignKey("warmup_pairs.id", ondelete="SET NULL"), nullable=True)
    recipient_mailbox_id = Column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="SET NULL"), nullable=True)
    
    event_type = Column(String, nullable=False) # "send", "reply"
    target_email = Column(String, nullable=False)
    
    subject = Column(String, nullable=True)
    body_preview = Column(Text, nullable=True)
    
    status = Column(String, default="pending") # "pending", "success", "failed"
    error_category = Column(String, nullable=True)
    result_detail = Column(Text, nullable=True)
    scheduled_for = Column(DateTime, nullable=True)
    
    sent_at = Column(DateTime, nullable=True)
    replied_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    mailbox = relationship("Mailbox", foreign_keys=[mailbox_id])
    recipient_mailbox = relationship("Mailbox", foreign_keys=[recipient_mailbox_id])
    pair = relationship("WarmupPair", foreign_keys=[pair_id])


class WarmupSetting(Base):
    __tablename__ = "warmup_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    is_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
