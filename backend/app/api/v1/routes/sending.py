from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.email import SendEmailRequest, SendEmailResponse
from app.services.smtp_service import SMTPManagerService

router = APIRouter()

@router.post("/send-email", response_model=SendEmailResponse)
def dispatch_outbound_email(req: SendEmailRequest, db: Session = Depends(get_db)):
    """Dispatch an email out strictly adhering to phase 4 abstraction"""
    service = SMTPManagerService(db)
    try:
        success, response = service.send_email(req)
        if not success:
            raise HTTPException(status_code=500, detail=response)
        
        return SendEmailResponse(success=True, message_id=response, status="queued")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
