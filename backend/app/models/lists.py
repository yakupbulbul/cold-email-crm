import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class LeadList(Base):
    __tablename__ = "lead_lists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    type = Column(String, nullable=False, default="static")
    filter_definition = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    members = relationship("LeadListMember", back_populates="lead_list", cascade="all, delete-orphan")
    campaigns = relationship("CampaignList", back_populates="lead_list", cascade="all, delete-orphan")


class LeadListMember(Base):
    __tablename__ = "lead_list_members"
    __table_args__ = (
        UniqueConstraint("list_id", "lead_id", name="uq_lead_list_members_list_id_lead_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    list_id = Column(UUID(as_uuid=True), ForeignKey("lead_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    lead_list = relationship("LeadList", back_populates="members")
    lead = relationship("Contact")


class CampaignList(Base):
    __tablename__ = "campaign_lists"
    __table_args__ = (
        UniqueConstraint("campaign_id", "list_id", name="uq_campaign_lists_campaign_id_list_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    list_id = Column(UUID(as_uuid=True), ForeignKey("lead_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    campaign = relationship("Campaign")
    lead_list = relationship("LeadList", back_populates="campaigns")
