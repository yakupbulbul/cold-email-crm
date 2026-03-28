from pydantic import BaseModel, UUID4
from typing import Optional, Dict

class ThreadIdRequest(BaseModel):
    thread_id: UUID4
    
class SuggestReplyRequest(BaseModel):
    thread_id: UUID4
    tone: Optional[str] = "professional"

class AiSummaryResponse(BaseModel):
    summary: str
    intent: Optional[str] = None
    tone: Optional[str] = None

class AiReplyResponse(BaseModel):
    reply_draft: str
