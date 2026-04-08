from pydantic import BaseModel, UUID4
from typing import Any, List, Optional
from datetime import datetime

class CampaignCreate(BaseModel):
    name: str
    mailbox_id: UUID4
    template_subject: str
    template_body: str
    daily_limit: int = 50
    campaign_type: str = "b2b"
    channel_type: str = "email"
    goal_type: str = "outreach"
    list_strategy: str = "list_based"
    compliance_mode: str = "standard"
    schedule_window: dict | None = None
    send_window_timezone: str | None = None


class CampaignUpdate(BaseModel):
    name: str
    mailbox_id: UUID4
    template_subject: str
    template_body: str
    daily_limit: int
    campaign_type: str = "b2b"
    channel_type: str = "email"
    goal_type: str = "outreach"
    list_strategy: str = "list_based"
    compliance_mode: str = "standard"
    schedule_window: dict | None = None
    send_window_timezone: str | None = None

class CampaignResponse(BaseModel):
    id: UUID4
    name: str
    status: str
    mailbox_id: UUID4 | None = None
    template_subject: str | None = None
    template_body: str | None = None
    daily_limit: int | None = None
    campaign_type: str | None = None
    channel_type: str | None = None
    goal_type: str | None = None
    list_strategy: str | None = None
    compliance_mode: str | None = None
    schedule_window: dict[str, Any] | None = None
    send_window_timezone: str | None = None
    lead_count: int | None = None
    sent_count: int | None = None
    reply_rate: str | int | None = None
    lists_summary: dict[str, Any] | None = None
    created_at: datetime
