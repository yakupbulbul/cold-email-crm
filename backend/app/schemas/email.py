from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID

class SendEmailRequest(BaseModel):
    mailbox_id: UUID
    to: List[str]
    cc: Optional[List[str]] = Field(default_factory=list)
    bcc: Optional[List[str]] = Field(default_factory=list)
    subject: str
    text_body: str
    html_body: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: Optional[str] = None

class SendEmailResponse(BaseModel):
    success: bool
    message_id: str
    status: str
    provider: str
    log_id: str | None = None


class SendEmailLogResponse(BaseModel):
    id: str
    mailbox_id: str | None = None
    campaign_id: str | None = None
    contact_id: str | None = None
    target_email: str
    subject: str | None = None
    delivery_status: str
    provider_message_id: str | None = None
    smtp_response: str | None = None
    created_at: str | None = None
