from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.email import SendEmailLogResponse, SendEmailRequest, SendEmailResponse
from app.services.smtp_service import SMTPManagerService, SMTPServiceError

router = APIRouter()

@router.post("/send-email", response_model=SendEmailResponse)
def dispatch_outbound_email(req: SendEmailRequest, db: Session = Depends(get_db)):
    service = SMTPManagerService(db)
    try:
        success, response = service.send_email(req)
        message_id, log_id = response.split("|", 1)
        return SendEmailResponse(success=success, message_id=message_id, status="sent", provider="smtp", log_id=log_id)
    except SMTPServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, "category": exc.category}) from exc


@router.get("/send-email/logs", response_model=list[SendEmailLogResponse])
def get_recent_send_logs(limit: int = 20, db: Session = Depends(get_db)):
    service = SMTPManagerService(db)
    return service.list_recent_logs(limit=limit)
