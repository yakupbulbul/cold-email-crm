from sqlalchemy.orm import Session
from app.models.core import Mailbox
from app.models.campaign import SendLog
from app.schemas.email import SendEmailRequest
from app.integrations.smtp.provider import MailcowSMTPProvider
import uuid

class SMTPManagerService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = MailcowSMTPProvider()

    def send_email(self, req: SendEmailRequest) -> tuple[bool, str]:
        mailbox = self.db.query(Mailbox).filter(Mailbox.id == req.mailbox_id).first()
        if not mailbox:
            raise ValueError("Mailbox not found")

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

        # Log the attempt in the database
        log = SendLog(
            mailbox_id=mailbox.id,
            target_email=", ".join(req.to),
            subject=req.subject,
            delivery_status="success" if success else "failed",
            smtp_response=message_id_or_error
        )
        self.db.add(log)
        self.db.commit()

        return success, message_id_or_error
