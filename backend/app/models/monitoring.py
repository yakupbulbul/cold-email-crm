import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base

class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_name = Column(String, index=True, nullable=False)
    worker_type = Column(String, nullable=False)
    status = Column(String, nullable=False) # healthy, degraded, failed
    last_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    metadata_blob = Column(JSON, nullable=True) # avoiding reserved keyword
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class JobLog(Base):
    __tablename__ = "job_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(String, index=True, nullable=False)
    job_type = Column(String, index=True, nullable=False) # imap_sync, smtp_send, etc
    status = Column(String, index=True, nullable=False) # queued, running, completed, failed, dead_letter
    idempotency_key = Column(String, index=True, nullable=True)
    payload_summary = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class CampaignPreflightCheck(Base):
    __tablename__ = "campaign_preflight_checks"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    check_name = Column(String, nullable=False) # e.g. spf_validation
    status = Column(String, nullable=False) # pass, warning, fail
    severity = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    metadata_blob = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class DeliverabilityEvent(Base):
    __tablename__ = "deliverability_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mailbox_id = Column(UUID(as_uuid=True), ForeignKey("mailboxes.id", ondelete="CASCADE"), nullable=True)
    domain_id = Column(UUID(as_uuid=True), ForeignKey("domains.id", ondelete="CASCADE"), nullable=True)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)
    contact_id = Column(UUID(as_uuid=True), nullable=True)
    event_type = Column(String, index=True, nullable=False) # sent, bounced, replied, suppressed
    provider_message_id = Column(String, nullable=True)
    smtp_response = Column(Text, nullable=True)
    metadata_blob = Column(JSON, nullable=True)
    occurred_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String, index=True, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=True)
    metadata_blob = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class SystemAlert(Base):
    __tablename__ = "system_alerts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type = Column(String, index=True, nullable=False)
    severity = Column(String, nullable=False) # info, warning, critical
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    source = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(UUID(as_uuid=True), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class NotificationReadState(Base):
    __tablename__ = "notification_read_states"
    __table_args__ = (
        UniqueConstraint("user_id", "notification_key", name="uq_notification_read_states_user_key"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_key = Column(String, nullable=False, index=True)
    read_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)


class QualityCheckRun(Base):
    __tablename__ = "quality_check_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    summary = Column(Text, nullable=True)
    triggered_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    results = relationship("QualityCheckResult", back_populates="run", cascade="all, delete-orphan", order_by="QualityCheckResult.created_at")


class QualityCheckResult(Base):
    __tablename__ = "quality_check_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("quality_check_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, default="info", index=True)
    message = Column(Text, nullable=False)
    entity_type = Column(String, nullable=True, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    href = Column(String, nullable=True)
    metadata_blob = Column(JSON, nullable=True)
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

    run = relationship("QualityCheckRun", back_populates="results")
