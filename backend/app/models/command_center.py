import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class OperatorTask(Base):
    __tablename__ = "operator_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="todo", index=True)
    priority = Column(String, nullable=False, default="normal", index=True)
    category = Column(String, nullable=False, default="manual", index=True)
    due_at = Column(DateTime, nullable=True, index=True)
    related_entity_type = Column(String, nullable=True, index=True)
    related_entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    metadata_blob = Column(JSON, nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class OperatorActionLog(Base):
    __tablename__ = "operator_action_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False, index=True)
    result = Column(String, nullable=False, default="info", index=True)
    message = Column(Text, nullable=False)
    related_entity_type = Column(String, nullable=True, index=True)
    related_entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    metadata_blob = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)


class DailyNote(Base):
    __tablename__ = "daily_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    note_date = Column(Date, nullable=False, unique=True, index=True, default=date.today)
    content = Column(Text, nullable=False, default="")
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class Runbook(Base):
    __tablename__ = "runbooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False, default="manual", index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    steps = relationship("RunbookStep", back_populates="runbook", cascade="all, delete-orphan", order_by="RunbookStep.step_order")


class RunbookStep(Base):
    __tablename__ = "runbook_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    runbook_id = Column(UUID(as_uuid=True), ForeignKey("runbooks.id", ondelete="CASCADE"), nullable=False, index=True)
    step_order = Column(Integer, nullable=False, default=1)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    default_status = Column(String, nullable=False, default="todo")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    runbook = relationship("Runbook", back_populates="steps")
