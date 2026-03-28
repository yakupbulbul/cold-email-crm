from pydantic import BaseModel, UUID4
from typing import List, Optional
from datetime import datetime

class CampaignCreate(BaseModel):
    name: str
    mailbox_id: UUID4
    template_subject: str
    template_body: str
    daily_limit: int = 50

class CampaignResponse(BaseModel):
    id: UUID4
    name: str
    status: str
    created_at: datetime
