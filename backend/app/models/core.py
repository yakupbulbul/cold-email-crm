import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, JSON, Text
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
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    mailboxes = relationship("Mailbox", back_populates="domain", cascade="all, delete-orphan")


class Mailbox(Base):
    __tablename__ = "mailboxes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    
    email = Column(String, unique=True, index=True, nullable=False)
    display_name = Column(String, nullable=False)

    provider_type = Column(String, default="mailcow", nullable=False, index=True)
    provider_status = Column(String, default="active", nullable=False)
    provider_mailbox_id = Column(String, nullable=True)
    provider_domain_id = Column(String, nullable=True)
    provider_config_status = Column(String, default="configured", nullable=False)
    last_provider_check_at = Column(DateTime, nullable=True)
    last_provider_check_status = Column(String, nullable=True)
    last_provider_check_message = Column(String, nullable=True)
    
    smtp_host = Column(String, nullable=False)
    smtp_port = Column(Integer, nullable=False)
    smtp_username = Column(String, nullable=False)
    smtp_password_encrypted = Column(String, nullable=False)
    smtp_security_mode = Column(String, default="starttls", nullable=False)
    
    imap_host = Column(String, nullable=False)
    imap_port = Column(Integer, nullable=False)
    imap_username = Column(String, nullable=False)
    imap_password_encrypted = Column(String, nullable=False)
    imap_security_mode = Column(String, default="ssl", nullable=False)
    oauth_enabled = Column(Boolean, default=False, nullable=False)
    oauth_provider = Column(String, nullable=True)
    oauth_connection_status = Column(String, nullable=True)
    oauth_last_checked_at = Column(DateTime, nullable=True)
    oauth_last_error = Column(String, nullable=True)
    inbox_sync_enabled = Column(Boolean, default=True, nullable=False)
    inbox_sync_status = Column(String, nullable=True)
    inbox_last_synced_at = Column(DateTime, nullable=True)
    inbox_last_success_at = Column(DateTime, nullable=True)
    inbox_last_error = Column(String, nullable=True)
    inbox_last_seen_uid = Column(String, nullable=True)
    
    warmup_enabled = Column(Boolean, default=False)
    daily_send_limit = Column(Integer, default=50) # Controls maximum capacity
    current_warmup_stage = Column(Integer, default=1)
    warmup_status = Column(String, nullable=True)
    warmup_last_checked_at = Column(DateTime, nullable=True)
    warmup_last_result = Column(String, nullable=True)
    warmup_block_reason = Column(String, nullable=True)
    
    status = Column(String, default="active")
    remote_mailcow_provisioned = Column(Boolean, default=False, nullable=False)
    smtp_last_checked_at = Column(DateTime, nullable=True)
    smtp_last_check_status = Column(String, nullable=True)
    smtp_last_check_category = Column(String, nullable=True)
    smtp_last_check_message = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    domain = relationship("Domain", back_populates="mailboxes")
    oauth_token = relationship("MailboxOAuthToken", back_populates="mailbox", uselist=False, cascade="all, delete-orphan")
    
    # Relationships to be injected
    # warmup_sent = relationship(...)


class MailProviderSetting(Base):
    __tablename__ = "mail_provider_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mailcow_enabled = Column(Boolean, default=True, nullable=False)
    google_workspace_enabled = Column(Boolean, default=False, nullable=False)
    default_provider = Column(String, default="mailcow", nullable=False)
    allow_existing_disabled_provider_mailboxes = Column(Boolean, default=False, nullable=False)
    mailcow_last_checked_at = Column(DateTime, nullable=True)
    mailcow_last_check_status = Column(String, nullable=True)
    mailcow_last_check_message = Column(String, nullable=True)
    google_workspace_last_checked_at = Column(DateTime, nullable=True)
    google_workspace_last_check_status = Column(String, nullable=True)
    google_workspace_last_check_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class MailboxOAuthToken(Base):
    __tablename__ = "mailbox_oauth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mailbox_id = Column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=False, unique=True)
    provider_type = Column(String, nullable=False, default="google_workspace")
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    scopes = Column(JSON, nullable=True)
    token_type = Column(String, nullable=True)
    external_account_email = Column(String, nullable=True)
    connection_status = Column(String, default="not_connected", nullable=False)
    last_refreshed_at = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    mailbox = relationship("Mailbox", back_populates="oauth_token")
