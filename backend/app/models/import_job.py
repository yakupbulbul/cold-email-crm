import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base

class LeadImportJob(Base):
    __tablename__ = "lead_import_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String, nullable=False)
    status = Column(String, default="pending") 
    # Statuses: pending, parsed, validated, confirmed, completed, failed
    
    total_rows = Column(Integer, default=0)
    valid_rows = Column(Integer, default=0)
    invalid_rows = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)
    imported_rows = Column(Integer, default=0)
    
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    rows = relationship("LeadImportRow", back_populates="job", cascade="all, delete-orphan")


class LeadImportRow(Base):
    __tablename__ = "lead_import_rows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("lead_import_jobs.id", ondelete="CASCADE"), nullable=False)
    
    row_index = Column(Integer, nullable=False)
    raw_data = Column(JSON, nullable=False)
    
    mapped_email = Column(String, nullable=True)
    mapped_first_name = Column(String, nullable=True)
    mapped_last_name = Column(String, nullable=True)
    mapped_company = Column(String, nullable=True)
    
    validation_status = Column(String, default="pending")
    # Statuses: valid, invalid, duplicate_in_file, duplicate_in_database, skipped, imported
    validation_reason = Column(Text, nullable=True)
    duplicate_type = Column(String, nullable=True) # "file" or "database"
    
    imported_contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    job = relationship("LeadImportJob", back_populates="rows")
    contact = relationship("Contact")
