from sqlalchemy.orm import Session
from app.models.core import Mailbox
from app.models.email import Thread, Message
from app.integrations.imap.provider import MailcowIMAPProvider
import email
from email.policy import default

class MessageParserService:
    @staticmethod
    def parse_raw_email(raw_email: bytes):
        msg = email.message_from_bytes(raw_email, policy=default)
        
        subject = msg.get("Subject", "")
        from_email = msg.get("From", "")
        to_email = msg.get("To", "")
        message_id = msg.get("Message-ID", "")
        in_reply_to = msg.get("In-Reply-To", "")
        references = msg.get("References", "")
        
        text_body = ""
        html_body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        text_body += payload.decode(errors="ignore")
                elif content_type == "text/html":
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_body += payload.decode(errors="ignore")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                text_body = payload.decode(errors="ignore")
            
        return {
            "subject": subject,
            "from_email": from_email,
            "to_emails": [to_email] if to_email else [],
            "message_id": message_id,
            "in_reply_to": in_reply_to,
            "references": references,
            "text_body": text_body,
            "html_body": html_body
        }

class ThreadResolverService:
    @staticmethod
    def resolve_thread(db: Session, mailbox: Mailbox, parsed_msg: dict) -> str:
        in_reply_to = parsed_msg.get("in_reply_to")
        
        if in_reply_to:
            existing_msg = db.query(Message).filter(Message.message_id_header == in_reply_to).first()
            if existing_msg:
                return existing_msg.thread_id
        
        new_thread = Thread(
            mailbox_id=mailbox.id,
            subject=parsed_msg.get("subject", "No Subject"),
            participants=[parsed_msg.get("from_email")] + parsed_msg.get("to_emails", [])
        )
        db.add(new_thread)
        db.commit()
        db.refresh(new_thread)
        return new_thread.id

class IMAPSyncManager:
    def __init__(self, db: Session):
        self.db = db
        self.provider = MailcowIMAPProvider()

    def sync_mailbox(self, mailbox_id: str):
        mailbox = self.db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
        if not mailbox:
            return
            
        raw_emails = self.provider.fetch_unread_messages(
            mailbox.imap_host, mailbox.imap_port, mailbox.imap_username, mailbox.imap_password_encrypted
        )
        
        for email_id, raw_bytes in raw_emails:
            parsed = MessageParserService.parse_raw_email(raw_bytes)
            
            if parsed["message_id"]:
                exists = self.db.query(Message).filter(Message.message_id_header == parsed["message_id"]).first()
                if exists:
                    self.provider.mark_as_read(mailbox.imap_host, mailbox.imap_port, mailbox.imap_username, mailbox.imap_password_encrypted, email_id)
                    continue
            
            thread_id = ThreadResolverService.resolve_thread(self.db, mailbox, parsed)
            
            msg = Message(
                thread_id=thread_id,
                mailbox_id=mailbox.id,
                direction="inbound",
                from_email=parsed["from_email"],
                to_emails=parsed["to_emails"],
                subject=parsed["subject"],
                text_body=parsed["text_body"],
                html_body=parsed["html_body"],
                message_id_header=parsed["message_id"],
                in_reply_to=parsed["in_reply_to"],
                references_header=parsed["references"]
            )
            self.db.add(msg)
            self.db.commit()
            
            self.provider.mark_as_read(mailbox.imap_host, mailbox.imap_port, mailbox.imap_username, mailbox.imap_password_encrypted, email_id)
