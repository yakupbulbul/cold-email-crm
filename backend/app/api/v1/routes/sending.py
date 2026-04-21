from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_current_active_user
from app.core.database import get_db
from app.models.core import Mailbox
from app.models.user import User
from app.schemas.email import SendEmailLogResponse, SendEmailRequest, SendEmailResponse
from app.services.command_center_service import record_command_action
from app.services.smtp_service import SMTPManagerService, SMTPServiceError

router = APIRouter()

@router.post("/send-email", response_model=SendEmailResponse)
def dispatch_outbound_email(
    req: SendEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = SMTPManagerService(db)
    mailbox = db.query(Mailbox).filter(Mailbox.id == req.mailbox_id).first()
    target_summary = ", ".join(req.to)
    try:
        success, response = service.send_email(req)
        message_id, log_id = response.split("|", 1)
        record_command_action(
            db,
            action_type="direct_send",
            source="send_email",
            result="success" if success else "failed",
            message=f"Direct send to {target_summary} {'succeeded' if success else 'failed'}.",
            related_entity_type="mailbox",
            related_entity_id=req.mailbox_id,
            actor=current_user,
            metadata={"mailbox_email": mailbox.email if mailbox else None, "target_email": target_summary, "log_id": log_id, "message_id": message_id},
        )
        return SendEmailResponse(
            success=success,
            message_id=message_id,
            status="sent",
            provider="smtp",
            log_id=log_id,
        )
    except SMTPServiceError as exc:
        record_command_action(
            db,
            action_type="direct_send",
            source="send_email",
            result="failed",
            message=f"Direct send to {target_summary} failed: {exc.message}",
            related_entity_type="mailbox",
            related_entity_id=req.mailbox_id,
            actor=current_user,
            metadata={"category": exc.category, "mailbox_email": mailbox.email if mailbox else None, "target_email": target_summary},
        )
        raise HTTPException(status_code=exc.status_code, detail={"message": exc.message, "category": exc.category}) from exc


@router.get("/send-email/logs", response_model=list[SendEmailLogResponse])
def get_recent_send_logs(limit: int = 20, db: Session = Depends(get_db)):
    service = SMTPManagerService(db)
    return service.list_recent_logs(limit=limit)
