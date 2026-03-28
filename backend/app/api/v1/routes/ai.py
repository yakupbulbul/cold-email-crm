from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.ai import ThreadIdRequest, SuggestReplyRequest, AiSummaryResponse, AiReplyResponse
from app.services.ai_service import AIProcessingService

router = APIRouter()

@router.post("/summarize", response_model=AiSummaryResponse)
def summarize_thread(req: ThreadIdRequest, db: Session = Depends(get_db)):
    service = AIProcessingService(db)
    summary = service.summarize_thread(str(req.thread_id))
    return AiSummaryResponse(
        summary=summary.summary,
        intent=summary.intent,
        tone=summary.tone
    )

@router.post("/reply-suggestion", response_model=AiReplyResponse)
def suggest_reply(req: SuggestReplyRequest, db: Session = Depends(get_db)):
    service = AIProcessingService(db)
    draft = service.suggest_reply(str(req.thread_id), req.tone)
    return AiReplyResponse(reply_draft=draft)
