from pydantic import BaseModel, UUID4

class WarmupControlRequest(BaseModel):
    mailbox_id: UUID4

class WarmupStatusResponse(BaseModel):
    mailbox_id: UUID4
    is_active: bool
    daily_limit: int
    sent_today: int
