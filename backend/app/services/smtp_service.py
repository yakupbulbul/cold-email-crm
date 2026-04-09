from sqlalchemy.orm import Session
from app.models.core import Mailbox
from app.models.campaign import SendLog
from app.schemas.email import SendEmailLogResponse, SendEmailRequest
from app.integrations.smtp.provider import MailcowSMTPProvider


class SMTPServiceError(Exception):
    def __init__(self, category: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.category = category
        self.message = message
        self.status_code = status_code

class SMTPManagerService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = MailcowSMTPProvider()

    def send_email(self, req: SendEmailRequest) -> tuple[bool, str]:
        mailbox = self.db.query(Mailbox).filter(Mailbox.id == req.mailbox_id).first()
        if not mailbox:
            raise SMTPServiceError("mailbox_not_found", "Mailbox not found.", status_code=404)
        if mailbox.status != "active":
            raise SMTPServiceError("mailbox_inactive", "Mailbox must be active before sending email.", status_code=409)

        success, message_id_or_error = self.provider.send_email(
            host=mailbox.smtp_host,
            port=mailbox.smtp_port,
            username=mailbox.smtp_username,
            password=mailbox.smtp_password_encrypted,
            from_email=mailbox.email,
            to_emails=req.to,
            subject=req.subject,
            text_body=req.text_body,
            html_body=req.html_body,
            cc_emails=req.cc,
            bcc_emails=req.bcc,
            in_reply_to=req.in_reply_to,
            references=req.references
        )

        safe_response = message_id_or_error if success else self._safe_provider_error(message_id_or_error)
        log = SendLog(
            mailbox_id=mailbox.id,
            target_email=", ".join(req.to),
            subject=req.subject,
            delivery_status="success" if success else "failed",
            smtp_response=safe_response,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        if not success:
            category, message, status_code = self._classify_provider_failure(message_id_or_error)
            raise SMTPServiceError(category, message, status_code=status_code)

        return success, f"{message_id_or_error}|{log.id}"

    def list_recent_logs(self, limit: int = 20) -> list[SendEmailLogResponse]:
        logs = self.db.query(SendLog).order_by(SendLog.created_at.desc()).limit(limit).all()
        return [
            SendEmailLogResponse(
                id=str(log.id),
                mailbox_id=str(log.mailbox_id) if log.mailbox_id else None,
                campaign_id=str(log.campaign_id) if log.campaign_id else None,
                contact_id=str(log.contact_id) if log.contact_id else None,
                target_email=log.target_email,
                subject=log.subject,
                delivery_status=log.delivery_status,
                smtp_response=log.smtp_response,
                created_at=log.created_at.isoformat() if log.created_at else None,
            )
            for log in logs
        ]

    def _safe_provider_error(self, raw_error: str) -> str:
        _category, message, _status_code = self._classify_provider_failure(raw_error)
        return message

    def _classify_provider_failure(self, raw_error: str) -> tuple[str, str, int]:
        normalized = (raw_error or "").lower()
        if "timed out" in normalized or "timeout" in normalized:
            return ("smtp_timeout", "SMTP server timed out before the email could be sent.", 504)
        if "auth" in normalized or "authentication" in normalized or "535" in normalized:
            return ("smtp_auth_failed", "SMTP rejected the mailbox credentials.", 502)
        if "refused" in normalized or "unreachable" in normalized or "name or service not known" in normalized:
            return ("smtp_unreachable", "SMTP server is unreachable from the backend environment.", 502)
        if "recipient refused" in normalized or "5.1.1" in normalized:
            return ("recipient_rejected", "SMTP rejected one or more recipients.", 422)
        return ("smtp_send_failed", "SMTP send failed before the message was accepted.", 502)
