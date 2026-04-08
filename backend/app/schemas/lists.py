from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class LeadListCreate(BaseModel):
    name: str
    description: str | None = None
    type: str = "static"
    filter_definition: dict[str, Any] | None = None


class LeadListUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None
    filter_definition: dict[str, Any] | None = None


class LeadListLeadPayload(BaseModel):
    lead_id: UUID


class LeadListLeadBulkPayload(BaseModel):
    lead_ids: list[UUID]


class CampaignListAttachPayload(BaseModel):
    list_id: UUID
