from datetime import datetime, timezone
from email.utils import formataddr

from sqlalchemy.orm import Session

from app.models.core import Mailbox
from app.models.campaign import SendLog
from app.models.email import Message
from app.schemas.email import SendEmailLogResponse, SendEmailRequest
from app.integrations.smtp.provider import MailcowSMTPProvider, SMTPDiagnosticResult
from app.services.mail_provider_service import MailProviderRegistry, ProviderUnavailableError
from app.services.imap_service import MessageParserService, ThreadResolverService


class SMTPServiceError(Exception):
    def __init__(self, category: str, message: str, status_code: int = 502, log_id: str | None = None):
        super().__init__(message)
        self.category = category
        self.message = message
        self.status_code = status_code
        self.log_id = log_id

class SMTPManagerService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = MailcowSMTPProvider()
        self.registry = MailProviderRegistry(db)

    def derive_security_mode(self, mailbox: Mailbox) -> str:
        configured = (mailbox.smtp_security_mode or "").strip().lower()
        if configured in {"starttls", "ssl", "plain"}:
            return configured
        return "ssl" if mailbox.smtp_port == 465 else "starttls"

    def build_sender_identity(self, mailbox: Mailbox) -> str:
        display_name = (mailbox.display_name or "").strip()
        if display_name:
            return formataddr((display_name, mailbox.email))
        return mailbox.email

    def check_mailbox_smtp(self, mailbox_id: str) -> dict:
        mailbox = self.db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
        if not mailbox:
            raise SMTPServiceError("mailbox_not_found", "Mailbox not found.", status_code=404)
        try:
            provider = self.registry.resolve_mailbox_provider(mailbox)
        except ProviderUnavailableError as exc:
            raise SMTPServiceError(exc.category, exc.message, status_code=exc.status_code) from exc

        self.provider = getattr(provider, "smtp", self.provider)
        try:
            result = provider.diagnose_smtp(mailbox)
        except Exception as exc:
            category, message, status_code = self._classify_provider_failure(str(exc))
            raise SMTPServiceError(category, message, status_code=status_code) from exc
        self._persist_smtp_check(mailbox, result)
        return self._serialize_diagnostic(result)

    def send_email(self, req: SendEmailRequest) -> tuple[bool, str]:
        mailbox = self.db.query(Mailbox).filter(Mailbox.id == req.mailbox_id).first()
        if not mailbox:
            raise SMTPServiceError("mailbox_not_found", "Mailbox not found.", status_code=404)
        if mailbox.status != "active":
            raise SMTPServiceError("mailbox_inactive", "Mailbox must be active before sending email.", status_code=409)
        try:
            provider = self.registry.resolve_mailbox_provider(mailbox)
        except ProviderUnavailableError as exc:
            raise SMTPServiceError(exc.category, exc.message, status_code=exc.status_code) from exc

        self.provider = getattr(provider, "smtp", self.provider)
        try:
            success, message_id_or_error = provider.send_email(
                mailbox,
                sender_email=mailbox.email,
                from_header=self.build_sender_identity(mailbox),
                to_emails=req.to,
                subject=req.subject,
                text_body=req.text_body,
                html_body=req.html_body,
                cc_emails=req.cc,
                bcc_emails=req.bcc,
                in_reply_to=req.in_reply_to,
                references=req.references,
            )
        except ProviderUnavailableError as exc:
            raise SMTPServiceError(exc.category, exc.message, status_code=exc.status_code) from exc
        except Exception as exc:
            category, message, status_code = self._classify_provider_failure(str(exc))
            raise SMTPServiceError(category, message, status_code=status_code) from exc

        safe_response = message_id_or_error if success else self._safe_provider_error(message_id_or_error)
        log = SendLog(
            mailbox_id=mailbox.id,
            target_email=", ".join(req.to),
            subject=req.subject,
            delivery_status="success" if success else "failed",
            provider_message_id=message_id_or_error if success else None,
            smtp_response=safe_response,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)

        if not success:
            category, message, status_code = self._classify_provider_failure(message_id_or_error)
            mailbox.smtp_last_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
            mailbox.smtp_last_check_status = "failed"
            mailbox.smtp_last_check_category = category
            mailbox.smtp_last_check_message = message
            self.db.add(mailbox)
            self.db.commit()
            raise SMTPServiceError(category, message, status_code=status_code, log_id=str(log.id))

        mailbox.smtp_last_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        mailbox.smtp_last_check_status = "healthy"
        mailbox.smtp_last_check_category = "ok"
        mailbox.smtp_last_check_message = "SMTP delivery succeeded."
        self.db.add(mailbox)
        self.db.commit()

        if success:
            self._persist_outbound_message(
                mailbox=mailbox,
                req=req,
                message_id=message_id_or_error,
            )

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
                provider_message_id=log.provider_message_id,
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
        if "dns resolution failed" in normalized:
            return ("dns_resolution_failed", "SMTP host could not be resolved from the backend environment.", 502)
        if "tls negotiation failed" in normalized:
            return ("tls_failed", "SMTP TLS negotiation failed for the selected security mode.", 502)
        if "authentication failed" in normalized:
            return ("smtp_auth_failed", "SMTP rejected the mailbox credentials.", 502)
        if "connection failed" in normalized:
            return ("smtp_unreachable", "SMTP server is unreachable from the backend environment.", 502)
        if "timed out" in normalized or "timeout" in normalized:
            return ("smtp_timeout", "SMTP server timed out before the email could be sent.", 504)
        if "auth" in normalized or "authentication" in normalized or "535" in normalized:
            return ("smtp_auth_failed", "SMTP rejected the mailbox credentials.", 502)
        if "refused" in normalized or "unreachable" in normalized or "name or service not known" in normalized:
            return ("smtp_unreachable", "SMTP server is unreachable from the backend environment.", 502)
        if "recipient refused" in normalized or "5.1.1" in normalized:
            return ("recipient_rejected", "SMTP rejected one or more recipients.", 422)
        return ("smtp_send_failed", "SMTP send failed before the message was accepted.", 502)

    def _persist_smtp_check(self, mailbox: Mailbox, result: SMTPDiagnosticResult) -> None:
        mailbox.smtp_last_checked_at = datetime.now(timezone.utc).replace(tzinfo=None)
        mailbox.smtp_last_check_status = result.status
        mailbox.smtp_last_check_category = result.category
        mailbox.smtp_last_check_message = result.message
        if not mailbox.smtp_security_mode:
            mailbox.smtp_security_mode = result.security_mode
        self.db.add(mailbox)
        self.db.commit()

    def _serialize_diagnostic(self, result: SMTPDiagnosticResult) -> dict:
        return {
            "status": result.status,
            "category": result.category,
            "message": result.message,
            "host": result.host,
            "port": result.port,
            "security_mode": result.security_mode,
            "dns_resolved": result.dns_resolved,
            "connected": result.connected,
            "tls_negotiated": result.tls_negotiated,
            "auth_succeeded": result.auth_succeeded,
        }

    def _persist_outbound_message(self, *, mailbox: Mailbox, req: SendEmailRequest, message_id: str) -> None:
        normalized_message_id = MessageParserService.normalize_message_id(message_id) or message_id
        referenced_ids = [
            MessageParserService.normalize_message_id(req.in_reply_to),
            *MessageParserService.normalize_references(req.references),
        ]
        thread = ThreadResolverService.ensure_thread_for_outbound(
            self.db,
            mailbox=mailbox,
            subject=req.subject,
            to_email=req.to[0] if req.to else None,
            message_ids=[message_id for message_id in referenced_ids if message_id],
            contact_id=req.contact_id,
            campaign_id=req.campaign_id,
        )
        thread.subject = req.subject or thread.subject
        thread.last_message_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if req.to:
            participant_email = req.to[0].strip().lower()
            thread.contact_email = participant_email
            participants = set(thread.participants or [])
            participants.add(mailbox.email.lower())
            participants.add(participant_email)
            thread.participants = sorted(address for address in participants if address)
        if req.contact_id and thread.contact_id is None:
            thread.contact_id = req.contact_id
        if req.campaign_id and thread.campaign_id is None:
            thread.campaign_id = req.campaign_id
        if req.contact_id or req.campaign_id:
            thread.linkage_status = "linked"

        existing_message = (
            self.db.query(Message)
            .filter(Message.mailbox_id == mailbox.id, Message.message_id_header == normalized_message_id)
            .first()
        )
        if existing_message is None:
            outbound_message = Message(
                thread_id=thread.id,
                mailbox_id=mailbox.id,
                direction="outbound",
                from_email=mailbox.email.lower(),
                to_emails=[address.lower() for address in req.to],
                cc_emails=[address.lower() for address in req.cc or []],
                bcc_emails=[address.lower() for address in req.bcc or []],
                subject=req.subject,
                text_body=req.text_body,
                html_body=req.html_body,
                message_id_header=normalized_message_id,
                in_reply_to=MessageParserService.normalize_message_id(req.in_reply_to),
                references_header=" ".join(MessageParserService.normalize_references(req.references)) or None,
                is_read=True,
                status="synced",
                sent_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
            self.db.add(thread)
            self.db.add(outbound_message)
            self.db.commit()
