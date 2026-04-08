from __future__ import annotations

from itertools import count

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.campaign import Campaign, Contact
from app.models.core import Domain, Mailbox
from app.models.suppression import SuppressionList
from app.models.user import User

_COUNTER = count(1)


def _next(prefix: str) -> str:
    return f"{prefix}-{next(_COUNTER)}"


def create_user(
    db: Session,
    *,
    email: str | None = None,
    password: str = "test1234",
    is_admin: bool = False,
    is_active: bool = True,
    full_name: str | None = None,
) -> User:
    user = User(
        email=email or f"{_next('user')}@example.com",
        hashed_password=get_password_hash(password),
        is_admin=is_admin,
        is_active=is_active,
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_domain(
    db: Session,
    *,
    name: str | None = None,
    status: str = "local_only",
    mailcow_status: str = "local_only",
) -> Domain:
    domain = Domain(
        name=name or f"{_next('domain')}.example.com",
        status=status,
        mailcow_status=mailcow_status,
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


def create_mailbox(
    db: Session,
    *,
    domain: Domain | None = None,
    email: str | None = None,
    display_name: str = "Test Mailbox",
    status: str = "active",
    daily_send_limit: int = 50,
) -> Mailbox:
    domain = domain or create_domain(db)
    local_part = _next("mailbox")
    mailbox = Mailbox(
        domain_id=domain.id,
        email=email or f"{local_part}@{domain.name}",
        display_name=display_name,
        status=status,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username=email or f"{local_part}@{domain.name}",
        smtp_password_encrypted="encrypted-smtp-password",
        imap_host="imap.example.com",
        imap_port=993,
        imap_username=email or f"{local_part}@{domain.name}",
        imap_password_encrypted="encrypted-imap-password",
        daily_send_limit=daily_send_limit,
    )
    db.add(mailbox)
    db.commit()
    db.refresh(mailbox)
    return mailbox


def create_campaign(
    db: Session,
    *,
    mailbox: Mailbox | None = None,
    name: str | None = None,
    status: str = "draft",
) -> Campaign:
    mailbox = mailbox or create_mailbox(db)
    campaign = Campaign(
        mailbox_id=mailbox.id,
        name=name or _next("campaign"),
        template_subject="Hello",
        template_body="World",
        status=status,
        daily_limit=25,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def create_contact(
    db: Session,
    *,
    email: str | None = None,
    first_name: str | None = "Test",
    last_name: str | None = "Lead",
    company: str | None = "Example Co",
    email_status: str = "unverified",
    verification_score: int | None = None,
    verification_integrity: str | None = None,
    is_disposable: bool = False,
    is_role_based: bool = False,
    is_suppressed: bool = False,
    verification_reasons: list[str] | None = None,
) -> Contact:
    contact = Contact(
        email=email or f"{_next('lead')}@example.com",
        first_name=first_name,
        last_name=last_name,
        company=company,
        email_status=email_status,
        verification_score=verification_score,
        verification_integrity=verification_integrity,
        is_disposable=is_disposable,
        is_role_based=is_role_based,
        is_suppressed=is_suppressed,
        verification_reasons=verification_reasons,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def campaign_payload(*, mailbox_id: str, name: str | None = None) -> dict:
    return {
        "name": name or _next("campaign"),
        "mailbox_id": str(mailbox_id),
        "template_subject": "Hello",
        "template_body": "World",
        "daily_limit": 25,
    }


def create_suppression_entry(
    db: Session,
    *,
    email: str | None = None,
    reason: str = "bounce",
) -> SuppressionList:
    entry = SuppressionList(
        email=email or f"{_next('suppressed')}@example.com",
        reason=reason,
        source="test-suite",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
