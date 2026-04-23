import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base

class SuppressionList(Base):
    __tablename__ = "suppression_list"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    reason = Column(String, nullable=False)
    source = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
