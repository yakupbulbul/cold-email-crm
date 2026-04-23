from __future__ import annotations

import email
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.policy import default
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.integrations.imap.provider import IMAPFetchedMessage, IMAPProviderError, MailcowIMAPProvider
from app.models.campaign import Campaign, Contact, SendLog
from app.models.core import Mailbox
from app.models.email import Message, Thread
from app.services.mail_provider_service import MailProviderRegistry, ProviderUnavailableError


MESSAGE_ID_RE = re.compile(r"<[^>]+>")


@dataclass
class InboxSyncOutcome:
    mailbox_id: str
    mailbox_email: str
    status: str
    detail: str
    fetched_count: int = 0
    imported_count: int = 0
    duplicate_count: int = 0
    thread_count: int = 0
    last_synced_at: str | None = None


class MessageParserService:
    @staticmethod
    def normalize_message_id(value: str | None) -> str | None:
        raw = (value or "").strip()
        if not raw:
            return None
        match = MESSAGE_ID_RE.search(raw)
        return match.group(0) if match else raw

    @classmethod
    def normalize_references(cls, value: str | None) -> list[str]:
        raw = (value or "").strip()
        if not raw:
            return []
        matches = MESSAGE_ID_RE.findall(raw)
        if matches:
            return matches
        return [piece.strip() for piece in raw.split() if piece.strip()]

    @staticmethod
    def _extract_bodies(msg: email.message.EmailMessage) -> tuple[str, str]:
        text_body = ""
        html_body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    continue
                content_type = part.get_content_type()
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                decoded = payload.decode(errors="ignore")
                if content_type == "text/plain":
                    text_body += decoded
                elif content_type == "text/html":
                    html_body += decoded
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                text_body = payload.decode(errors="ignore")
        return text_body.strip(), html_body.strip()

    @classmethod
    def parse_raw_email(cls, raw_email: bytes) -> dict:
        msg = email.message_from_bytes(raw_email, policy=default)
        from_name, from_email = parseaddr(msg.get("From", ""))
        to_addresses = [address for _, address in getaddresses(msg.get_all("To", [])) if address]
        cc_addresses = [address for _, address in getaddresses(msg.get_all("Cc", [])) if address]
        subject = (msg.get("Subject", "") or "").strip()
        message_id = cls.normalize_message_id(msg.get("Message-ID"))
        in_reply_to = cls.normalize_message_id(msg.get("In-Reply-To"))
        references = cls.normalize_references(msg.get("References"))
        text_body, html_body = cls._extract_bodies(msg)
        sent_at = None
        date_header = msg.get("Date")
        if date_header:
            try:
                parsed = parsedate_to_datetime(date_header)
                sent_at = parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
            except Exception:
                sent_at = None

        return {
            "subject": subject,
            "from_name": from_name or None,
            "from_email": from_email or "",
            "to_emails": to_addresses,
            "cc_emails": cc_addresses,
            "message_id": message_id,
            "in_reply_to": in_reply_to,
            "references": references,
            "text_body": text_body,
            "html_body": html_body,
            "sent_at": sent_at,
        }


class ThreadResolverService:
    @staticmethod
    def _thread_for_existing_message(db: Session, message_ids: list[str]) -> Thread | None:
        if not message_ids:
            return None
        existing_message = (
            db.query(Message)
            .filter(Message.message_id_header.in_(message_ids))
            .order_by(Message.created_at.desc())
            .first()
        )
        if existing_message is None:
            return None
        return db.query(Thread).filter(Thread.id == existing_message.thread_id).first()

    @staticmethod
    def _thread_for_send_log(db: Session, mailbox: Mailbox, message_ids: list[str]) -> Thread | None:
        if not message_ids:
            return None
        send_log = (
            db.query(SendLog)
            .filter(
                SendLog.mailbox_id == mailbox.id,
                SendLog.provider_message_id.in_(message_ids),
            )
            .order_by(SendLog.created_at.desc())
            .first()
        )
        if send_log is None:
            return None

        participant_email = (send_log.target_email or "").split(",", 1)[0].strip().lower() or None
        existing_thread = (
            db.query(Thread)
            .filter(
                Thread.mailbox_id == mailbox.id,
                Thread.contact_id == send_log.contact_id,
                Thread.campaign_id == send_log.campaign_id,
            )
            .order_by(Thread.last_message_at.desc(), Thread.created_at.desc())
            .first()
        )
        if existing_thread is not None:
            return existing_thread

        return ThreadResolverService._create_thread(
            db,
            mailbox=mailbox,
            subject=send_log.subject or "No Subject",
            contact_email=participant_email,
            participants=[participant_email, mailbox.email] if participant_email else [mailbox.email],
            contact_id=send_log.contact_id,
            campaign_id=send_log.campaign_id,
            linkage_status="linked" if send_log.contact_id or send_log.campaign_id else "mailbox_only",
        )

    @staticmethod
    def _thread_for_contact(db: Session, mailbox: Mailbox, contact_email: str) -> Thread | None:
        if not contact_email:
            return None
        return (
            db.query(Thread)
            .filter(Thread.mailbox_id == mailbox.id, Thread.contact_email == contact_email.lower())
            .order_by(Thread.last_message_at.desc(), Thread.created_at.desc())
            .first()
        )

    @staticmethod
    def _create_thread(
        db: Session,
        *,
        mailbox: Mailbox,
        subject: str,
        contact_email: str | None,
        participants: list[str],
        contact_id: UUID | None = None,
        campaign_id: UUID | None = None,
        linkage_status: str = "unlinked",
    ) -> Thread:
        thread = Thread(
            mailbox_id=mailbox.id,
            campaign_id=campaign_id,
            contact_id=contact_id,
            subject=subject or "No Subject",
            contact_email=(contact_email or "").lower() or None,
            linkage_status=linkage_status,
            participants=[participant for participant in participants if participant],
            last_message_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(thread)
        db.flush()
        return thread

    @staticmethod
    def ensure_thread_for_outbound(
        db: Session,
        *,
        mailbox: Mailbox,
        subject: str,
        to_email: str | None,
        message_ids: list[str],
        contact_id: UUID | None = None,
        campaign_id: UUID | None = None,
    ) -> Thread:
        thread = ThreadResolverService._thread_for_existing_message(db, message_ids)
        if thread is not None:
            return thread

        participant_email = (to_email or "").strip().lower() or None
        if participant_email:
            existing_thread = (
                db.query(Thread)
                .filter(
                    Thread.mailbox_id == mailbox.id,
                    Thread.contact_email == participant_email,
                )
                .order_by(Thread.last_message_at.desc(), Thread.created_at.desc())
                .first()
            )
            if existing_thread is not None:
                if existing_thread.contact_id is None and contact_id is not None:
                    existing_thread.contact_id = contact_id
                if existing_thread.campaign_id is None and campaign_id is not None:
                    existing_thread.campaign_id = campaign_id
                if existing_thread.linkage_status == "unlinked" and (contact_id or campaign_id):
                    existing_thread.linkage_status = "linked"
                return existing_thread

        return ThreadResolverService._create_thread(
            db,
            mailbox=mailbox,
            subject=subject,
            contact_email=participant_email,
            participants=[participant_email, mailbox.email] if participant_email else [mailbox.email],
            contact_id=contact_id,
            campaign_id=campaign_id,
            linkage_status="linked" if (contact_id or campaign_id) else "mailbox_only",
        )

    @staticmethod
    def resolve_inbound_thread(db: Session, mailbox: Mailbox, parsed_msg: dict) -> Thread:
        referenced_ids = [parsed_msg.get("in_reply_to")] + parsed_msg.get("references", [])
        normalized_ids = [message_id for message_id in referenced_ids if message_id]

        existing_thread = ThreadResolverService._thread_for_existing_message(db, normalized_ids)
        if existing_thread is not None:
            return existing_thread

        logged_thread = ThreadResolverService._thread_for_send_log(db, mailbox, normalized_ids)
        if logged_thread is not None:
            return logged_thread

        sender_email = (parsed_msg.get("from_email") or "").strip().lower()
        contact = db.query(Contact).filter(Contact.email == sender_email).first() if sender_email else None
        existing_thread = ThreadResolverService._thread_for_contact(db, mailbox, sender_email)
        if existing_thread is not None:
            if existing_thread.contact_id is None and contact is not None:
                existing_thread.contact_id = contact.id
            if existing_thread.linkage_status == "unlinked" and contact is not None:
                existing_thread.linkage_status = "linked"
            return existing_thread

        return ThreadResolverService._create_thread(
            db,
            mailbox=mailbox,
            subject=parsed_msg.get("subject") or "No Subject",
            contact_email=sender_email,
            participants=[sender_email, mailbox.email],
            contact_id=contact.id if contact else None,
            linkage_status="linked" if contact else "unlinked",
        )


class IMAPSyncManager:
    def __init__(self, db: Session):
        self.db = db
        self.provider = MailcowIMAPProvider()
        self.registry = MailProviderRegistry(db)

    def diagnose_mailbox(self, mailbox: Mailbox) -> dict:
        if not mailbox.inbox_sync_enabled:
            return {"status": "disabled", "detail": "Inbox sync is disabled for this mailbox."}
        if mailbox.status != "active":
            return {"status": "disabled", "detail": "Mailbox is not active."}
        if not mailbox.imap_host or not mailbox.imap_username or not mailbox.imap_password_encrypted:
            return {"status": "not_configured", "detail": "IMAP settings are incomplete."}
        try:
            provider = self.registry.resolve_mailbox_provider(mailbox)
        except ProviderUnavailableError as exc:
            return {"status": "disabled", "detail": exc.message, "category": exc.category}
        self.provider = getattr(provider, "imap", self.provider)
        try:
            result = provider.diagnose_imap(mailbox)
        except Exception as exc:
            return {"status": "failing", "detail": str(exc), "category": "imap_failed"}
        return {"status": result.status, "detail": result.message, "category": result.category}

    def sync_mailbox(self, mailbox_id: str | UUID) -> InboxSyncOutcome:
        mailbox = self.db.query(Mailbox).filter(Mailbox.id == mailbox_id).first()
        if mailbox is None:
            raise ValueError("Mailbox not found")

        if not mailbox.inbox_sync_enabled:
            mailbox.inbox_sync_status = "disabled"
            mailbox.inbox_last_error = "Inbox sync is disabled for this mailbox."
            self.db.add(mailbox)
            self.db.commit()
            return InboxSyncOutcome(
                mailbox_id=str(mailbox.id),
                mailbox_email=mailbox.email,
                status="disabled",
                detail=mailbox.inbox_last_error,
            )

        if mailbox.status != "active":
            mailbox.inbox_sync_status = "disabled"
            mailbox.inbox_last_error = "Mailbox must be active for inbox sync."
            self.db.add(mailbox)
            self.db.commit()
            return InboxSyncOutcome(
                mailbox_id=str(mailbox.id),
                mailbox_email=mailbox.email,
                status="disabled",
                detail=mailbox.inbox_last_error,
            )

        if not mailbox.imap_host or not mailbox.imap_username or not mailbox.imap_password_encrypted:
            mailbox.inbox_sync_status = "not_configured"
            mailbox.inbox_last_error = "IMAP settings are incomplete."
            self.db.add(mailbox)
            self.db.commit()
            return InboxSyncOutcome(
                mailbox_id=str(mailbox.id),
                mailbox_email=mailbox.email,
                status="not_configured",
                detail=mailbox.inbox_last_error,
            )

        try:
            provider = self.registry.resolve_mailbox_provider(mailbox)
            self.provider = getattr(provider, "imap", self.provider)
            fetched_messages = provider.sync_inbox(mailbox)
        except ProviderUnavailableError as exc:
            mailbox.inbox_sync_status = "disabled"
            mailbox.inbox_last_synced_at = datetime.now(timezone.utc).replace(tzinfo=None)
            mailbox.inbox_last_error = exc.message
            self.db.add(mailbox)
            self.db.commit()
            return InboxSyncOutcome(
                mailbox_id=str(mailbox.id),
                mailbox_email=mailbox.email,
                status="disabled",
                detail=exc.message,
                last_synced_at=mailbox.inbox_last_synced_at.isoformat() if mailbox.inbox_last_synced_at else None,
            )
        except IMAPProviderError as exc:
            mailbox.inbox_sync_status = "failing"
            mailbox.inbox_last_synced_at = datetime.now(timezone.utc).replace(tzinfo=None)
            mailbox.inbox_last_error = exc.message
            self.db.add(mailbox)
            self.db.commit()
            return InboxSyncOutcome(
                mailbox_id=str(mailbox.id),
                mailbox_email=mailbox.email,
                status="failing",
                detail=exc.message,
                last_synced_at=mailbox.inbox_last_synced_at.isoformat() if mailbox.inbox_last_synced_at else None,
            )

        imported_count = 0
        duplicate_count = 0
        thread_ids: set[str] = set()
        last_seen_uid = mailbox.inbox_last_seen_uid
        for fetched in fetched_messages:
            parsed = MessageParserService.parse_raw_email(fetched.raw_bytes)
            normalized_message_id = parsed["message_id"]

            exists_query = self.db.query(Message).filter(Message.mailbox_id == mailbox.id)
            if normalized_message_id:
                exists_query = exists_query.filter(Message.message_id_header == normalized_message_id)
            else:
                exists_query = exists_query.filter(Message.imap_uid == fetched.uid)
            if exists_query.first() is not None:
                duplicate_count += 1
                last_seen_uid = fetched.uid
                continue

            thread = ThreadResolverService.resolve_inbound_thread(self.db, mailbox, parsed)
            thread.subject = parsed.get("subject") or thread.subject or "No Subject"
            if parsed.get("from_email"):
                thread.contact_email = (parsed["from_email"] or "").lower()
            participants = set(thread.participants or [])
            participants.add(mailbox.email)
            if parsed.get("from_email"):
                participants.add(parsed["from_email"].lower())
            for address in parsed.get("to_emails", []):
                participants.add(address.lower())
            thread.participants = sorted(address for address in participants if address)
            message_timestamp = fetched.received_at or parsed.get("sent_at") or datetime.now(timezone.utc).replace(tzinfo=None)
            thread.last_message_at = message_timestamp

            msg = Message(
                thread_id=thread.id,
                mailbox_id=mailbox.id,
                direction="inbound",
                from_email=(parsed.get("from_email") or "").lower(),
                to_emails=[address.lower() for address in parsed.get("to_emails", [])],
                cc_emails=[address.lower() for address in parsed.get("cc_emails", [])],
                subject=parsed.get("subject"),
                text_body=parsed.get("text_body"),
                html_body=parsed.get("html_body"),
                message_id_header=normalized_message_id,
                imap_uid=fetched.uid,
                in_reply_to=parsed.get("in_reply_to"),
                references_header=" ".join(parsed.get("references", [])) or None,
                is_read=fetched.is_read,
                status="synced",
                received_at=message_timestamp,
            )
            self.db.add(thread)
            self.db.add(msg)
            self.db.flush()
            thread_ids.add(str(thread.id))
            imported_count += 1
            last_seen_uid = fetched.uid

            if thread.contact_id is not None:
                contact = self.db.query(Contact).filter(Contact.id == thread.contact_id).first()
                if contact is not None:
                    contact.last_replied_at = message_timestamp
                    self.db.add(contact)

        mailbox.inbox_last_seen_uid = last_seen_uid
        mailbox.inbox_last_synced_at = datetime.now(timezone.utc).replace(tzinfo=None)
        mailbox.inbox_sync_status = "healthy"
        mailbox.inbox_last_error = None
        mailbox.inbox_last_success_at = mailbox.inbox_last_synced_at
        self.db.add(mailbox)
        self.db.commit()

        return InboxSyncOutcome(
            mailbox_id=str(mailbox.id),
            mailbox_email=mailbox.email,
            status="healthy",
            detail="Inbox sync completed.",
            fetched_count=len(fetched_messages),
            imported_count=imported_count,
            duplicate_count=duplicate_count,
            thread_count=len(thread_ids),
            last_synced_at=mailbox.inbox_last_synced_at.isoformat() if mailbox.inbox_last_synced_at else None,
        )


def build_inbox_thread_summary(thread: Thread) -> dict:
    ordered_messages = sorted(
        thread.messages,
        key=lambda item: item.received_at or item.sent_at or item.created_at,
        reverse=True,
    )
    latest_message = ordered_messages[0] if ordered_messages else None
    unread_count = sum(1 for message in thread.messages if message.direction == "inbound" and not message.is_read)
    contact_name = None
    if getattr(thread, "contact", None) is not None:
        first_name = (thread.contact.first_name or "").strip()
        last_name = (thread.contact.last_name or "").strip()
        full_name = " ".join(part for part in [first_name, last_name] if part).strip()
        contact_name = full_name or None
    return {
        "id": str(thread.id),
        "subject": thread.subject or "",
        "mailbox_id": str(thread.mailbox_id),
        "mailbox_email": thread.mailbox.email if thread.mailbox else None,
        "mailbox_provider": thread.mailbox.provider_type if thread.mailbox else None,
        "contact_email": thread.contact_email or "",
        "contact_name": contact_name,
        "campaign_id": str(thread.campaign_id) if thread.campaign_id else None,
        "campaign_name": thread.campaign.name if getattr(thread, "campaign", None) else None,
        "contact_id": str(thread.contact_id) if thread.contact_id else None,
        "linkage_status": thread.linkage_status,
        "participants": thread.participants or [],
        "status": "active",
        "last_message_at": (thread.last_message_at or thread.created_at).isoformat(),
        "snippet": ((latest_message.text_body or latest_message.subject or "")[:160] if latest_message else ""),
        "unread": unread_count > 0,
        "unread_count": unread_count,
        "last_message_direction": latest_message.direction if latest_message else None,
        "last_message_preview": (latest_message.text_body or latest_message.subject or "")[:240] if latest_message else "",
    }


def build_inbox_message_payload(message: Message) -> dict:
    return {
        "id": str(message.id),
        "thread_id": str(message.thread_id),
        "direction": message.direction,
        "subject": message.subject or "",
        "body_text": message.text_body or "",
        "body_html": message.html_body,
        "from_address": message.from_email,
        "to_address": ", ".join(message.to_emails or []),
        "cc_address": ", ".join(message.cc_emails or []),
        "is_read": message.is_read,
        "sent_at": (message.sent_at or message.received_at or message.created_at).isoformat(),
    }


def infer_inbox_blockers(*, mailboxes: list[Mailbox], threads_count: int, workers_enabled: bool, auto_sync_enabled: bool) -> list[dict]:
    blockers: list[dict] = []
    if not mailboxes:
        blockers.append({"code": "no_mailboxes", "message": "No mailboxes are configured for inbox sync yet."})
        return blockers

    active_mailboxes = [mailbox for mailbox in mailboxes if mailbox.status == "active"]
    enabled_mailboxes = [mailbox for mailbox in active_mailboxes if mailbox.inbox_sync_enabled]
    if not enabled_mailboxes:
        blockers.append({"code": "inbox_disabled", "message": "Inbox sync is disabled for every active mailbox."})
    if not workers_enabled:
        blockers.append({"code": "workers_disabled", "message": "Background workers are disabled, so automatic inbox sync is not running."})
    if workers_enabled and not auto_sync_enabled:
        blockers.append({"code": "auto_sync_disabled", "message": "Automatic inbox sync is disabled in the current runtime configuration."})

    failing_mailboxes = [mailbox for mailbox in enabled_mailboxes if mailbox.inbox_sync_status == "failing"]
    if failing_mailboxes:
        blockers.append({"code": "imap_failed", "message": f"IMAP sync failed for {len(failing_mailboxes)} mailbox(es)."})

    never_synced = [mailbox for mailbox in enabled_mailboxes if mailbox.inbox_last_synced_at is None]
    if enabled_mailboxes and len(never_synced) == len(enabled_mailboxes):
        blockers.append({"code": "never_synced", "message": "Inbox sync has never been run for the enabled mailboxes."})

    if threads_count == 0 and enabled_mailboxes and not failing_mailboxes and not never_synced:
        blockers.append({"code": "no_messages", "message": "Inbox sync is healthy, but no messages have been ingested yet."})

    return blockers
