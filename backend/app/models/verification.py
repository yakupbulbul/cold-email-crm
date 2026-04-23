import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base

class EmailVerificationLog(Base):
    __tablename__ = "email_verification_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True)
    email = Column(String, nullable=False, index=True)
    
    # Layer A Check outputs
    syntax_valid = Column(Boolean, default=False)
    domain_valid = Column(Boolean, default=False)
    mx_valid = Column(Boolean, default=False)
    disposable = Column(Boolean, default=False)
    role_based = Column(Boolean, default=False)
    duplicate = Column(Boolean, default=False)
    blocked = Column(Boolean, default=False)
    suppressed = Column(Boolean, default=False)
    
    # Layer B (Advanced)
    smtp_check_result = Column(String, nullable=True)
    catch_all_result = Column(String, nullable=True)
    
    verification_score = Column(Integer, default=0)
    verification_integrity = Column(String, nullable=True)
    verification_reasons = Column(JSON, nullable=True)
    final_status = Column(String, default="pending") 
    # Statuses: valid, risky, invalid, duplicate, disposable, role_based, no_mx, blocked, suppressed
    
    checked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    contact = relationship("Contact")
