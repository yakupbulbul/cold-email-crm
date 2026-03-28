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
