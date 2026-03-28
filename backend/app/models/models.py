import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from app.database import Base

class Domain(Base):
    __tablename__ = "domains"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    mailboxes = relationship("Mailbox", back_populates="domain", cascade="all, delete")

class Mailbox(Base):
    __tablename__ = "mailboxes"
    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"))
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    smtp_host = Column(String, default="mail.example.com")
    smtp_port = Column(Integer, default=587)
    imap_host = Column(String, default="mail.example.com")
    imap_port = Column(Integer, default=143)
    is_active = Column(Boolean, default=True)
    warmup_enabled = Column(Boolean, default=False)
    daily_limit = Column(Integer, default=50)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    domain = relationship("Domain", back_populates="mailboxes")
    threads = relationship("Thread", back_populates="mailbox")
    campaigns = relationship("Campaign", back_populates="mailbox")

class ContactStatus(str, enum.Enum):
    NEW = "new"
    CONTACTED = "contacted"
    REPLIED = "replied"
    UNSUBSCRIBED = "unsubscribed"

class Contact(Base):
    __tablename__ = "contacts"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    status = Column(Enum(ContactStatus), default=ContactStatus.NEW)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    campaign_leads = relationship("CampaignLead", back_populates="contact")
    threads = relationship("Thread", back_populates="contact")

class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True, index=True)
    mailbox_id = Column(Integer, ForeignKey("mailboxes.id"))
    name = Column(String, nullable=False)
    subject_template = Column(String, nullable=False)
    body_template = Column(Text, nullable=False)
    is_active = Column(Boolean, default=False)
    daily_limit = Column(Integer, default=50)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    mailbox = relationship("Mailbox", back_populates="campaigns")
    leads = relationship("CampaignLead", back_populates="campaign", cascade="all, delete")

class CampaignLead(Base):
    __tablename__ = "campaign_leads"
    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    contact_id = Column(Integer, ForeignKey("contacts.id"))
    status = Column(String, default="pending") # pending, sent, failed
    sent_at = Column(DateTime, nullable=True)

    campaign = relationship("Campaign", back_populates="leads")
    contact = relationship("Contact", back_populates="campaign_leads")

class Thread(Base):
    __tablename__ = "threads"
    id = Column(Integer, primary_key=True, index=True)
    mailbox_id = Column(Integer, ForeignKey("mailboxes.id"))
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    subject = Column(String, nullable=True)
    snippet = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    mailbox = relationship("Mailbox", back_populates="threads")
    contact = relationship("Contact", back_populates="threads")
    messages = relationship("Message", back_populates="thread", cascade="all, delete")
    ai_summary = relationship("AiSummary", back_populates="thread", uselist=False, cascade="all, delete")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id"))
    message_id = Column(String, unique=True, index=True, nullable=False) # IMAP Message-ID
    in_reply_to = Column(String, nullable=True)
    from_email = Column(String, nullable=False)
    to_email = Column(String, nullable=False)
    text_content = Column(Text, nullable=True)
    html_content = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    is_from_me = Column(Boolean, default=False)

    thread = relationship("Thread", back_populates="messages")

class AiSummary(Base):
    __tablename__ = "ai_summaries"
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), unique=True)
    summary_text = Column(Text, nullable=False)
    intent_classification = Column(String, nullable=True) # e.g. "positive reply", "not interested"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    thread = relationship("Thread", back_populates="ai_summary")

class WarmupPair(Base):
    __tablename__ = "warmup_pairs"
    id = Column(Integer, primary_key=True, index=True)
    mailbox_a_id = Column(Integer, ForeignKey("mailboxes.id"))
    mailbox_b_id = Column(Integer, ForeignKey("mailboxes.id"))
    is_active = Column(Boolean, default=True)

    mailbox_a = relationship("Mailbox", foreign_keys=[mailbox_a_id])
    mailbox_b = relationship("Mailbox", foreign_keys=[mailbox_b_id])

class WarmupEvent(Base):
    __tablename__ = "warmup_events"
    id = Column(Integer, primary_key=True, index=True)
    pair_id = Column(Integer, ForeignKey("warmup_pairs.id"))
    sender_id = Column(Integer, ForeignKey("mailboxes.id"))
    recipient_id = Column(Integer, ForeignKey("mailboxes.id"))
    event_type = Column(String, nullable=False) # "send", "reply"
    status = Column(String, default="success") # "success", "failed"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    pair = relationship("WarmupPair")
    sender = relationship("Mailbox", foreign_keys=[sender_id])
    recipient = relationship("Mailbox", foreign_keys=[recipient_id])
