import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base

class Contact(Base):
    __tablename__ = "contacts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    company = Column(String, nullable=True)

    job_title = Column(String, nullable=True)
    website = Column(String, nullable=True)
    country = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    persona = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    contact_type = Column(String, nullable=True)
    consent_status = Column(String, default="unknown")
    unsubscribe_status = Column(String, default="subscribed")
    engagement_score = Column(Integer, default=0)
    contact_status = Column(String, default="active")
    
    email_status = Column(String, default="unverified")
    verification_score = Column(Integer, nullable=True)
    verification_integrity = Column(String, nullable=True)
    is_disposable = Column(Boolean, default=False)
    is_role_based = Column(Boolean, default=False)
    is_suppressed = Column(Boolean, default=False)
    verification_reasons = Column(JSON, nullable=True)
    
    source = Column(String, nullable=True)
    source_file_name = Column(String, nullable=True)
    source_import_job_id = Column(UUID(as_uuid=True), ForeignKey("lead_import_jobs.id", ondelete="SET NULL"), nullable=True)
    
    last_verified_at = Column(DateTime, nullable=True)
    last_contacted_at = Column(DateTime, nullable=True)
    last_replied_at = Column(DateTime, nullable=True)
    
    tags = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    status = Column(String, default="draft") # "draft", "active", "paused", "completed", "archived"
    
    mailbox_id = Column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="SET NULL"), nullable=True)
    daily_limit = Column(Integer, default=50)
    campaign_type = Column(String, default="b2b")
    channel_type = Column(String, default="email")
    goal_type = Column(String, default="outreach")
    list_strategy = Column(String, default="list_based")
    compliance_mode = Column(String, default="standard")
    schedule_window = Column(JSON, nullable=True)
    send_window_timezone = Column(String, nullable=True)
    
    template_subject = Column(String, nullable=False)
    template_body = Column(Text, nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    mailbox = relationship("Mailbox")
    leads = relationship("CampaignLead", back_populates="campaign", cascade="all, delete-orphan")
    sequence_steps = relationship("CampaignSequenceStep", back_populates="campaign", cascade="all, delete-orphan", order_by="CampaignSequenceStep.step_number")


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CampaignSequenceStep(Base):
    __tablename__ = "campaign_sequence_steps"
    __table_args__ = (
        UniqueConstraint("campaign_id", "step_number", name="uq_campaign_sequence_steps_campaign_step"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    delay_days = Column(Integer, default=0, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    stop_on_reply = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    campaign = relationship("Campaign", back_populates="sequence_steps")


class CampaignLead(Base):
    __tablename__ = "campaign_leads"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False)
    
    status = Column(String, default="scheduled") # "scheduled", "sent", "replied", "bounced"
    sequence_step_index = Column(Integer, default=1, nullable=False)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    replied_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    campaign = relationship("Campaign", back_populates="leads")
    contact = relationship("Contact")


class SendLog(Base):
    __tablename__ = "send_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mailbox_id = Column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="SET NULL"), nullable=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    
    target_email = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    delivery_status = Column(String, nullable=False) # "success", "failed"
    provider_message_id = Column(String, nullable=True)
    smtp_response = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
