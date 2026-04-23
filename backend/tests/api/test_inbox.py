"""Inbox endpoint tests."""
import uuid
from datetime import datetime, timedelta, timezone

from app.models.campaign import Contact, SendLog
from app.models.core import Domain, Mailbox
from app.models.email import Message, Thread


def _create_mailbox(db, email="sales@inbox-example.com"):
    domain = Domain(name=email.split("@", 1)[1], mailcow_status="verified")
    db.add(domain)
    db.flush()
    mailbox = Mailbox(
        domain_id=domain.id,
        email=email,
        display_name="Sales",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username=email,
        smtp_password_encrypted="encrypted",
        imap_host="imap.example.com",
        imap_port=993,
        imap_username=email,
        imap_password_encrypted="encrypted",
    )
    db.add(mailbox)
    db.flush()
    return mailbox


def test_list_threads_returns_latest_snippet_and_unread(client, auth_headers, db):
    mailbox = _create_mailbox(db)

    thread = Thread(
        mailbox_id=mailbox.id,
        external_thread_id="thread-1",
        subject="Interested in a demo",
        participants=["buyer@example.com", mailbox.email],
        contact_email="buyer@example.com",
        last_message_at=datetime.now(timezone.utc),
    )
    db.add(thread)
    db.flush()

    db.add_all(
        [
            Message(
                thread_id=thread.id,
                mailbox_id=mailbox.id,
                direction="outbound",
                from_email=mailbox.email,
                to_emails=["buyer@example.com"],
                subject="Intro",
                text_body="Happy to help.",
                is_read=True,
                sent_at=datetime.now(timezone.utc) - timedelta(hours=2),
            ),
            Message(
                thread_id=thread.id,
                mailbox_id=mailbox.id,
                direction="inbound",
                from_email="buyer@example.com",
                to_emails=[mailbox.email],
                subject="Interested in a demo",
                text_body="Can you show me the platform this week?",
                is_read=False,
                received_at=datetime.now(timezone.utc) - timedelta(hours=1),
            ),
        ]
    )
    db.commit()

    response = client.get("/api/v1/inbox/threads", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["contact_email"] == "buyer@example.com"
    assert payload[0]["unread"] is True
    assert payload[0]["unread_count"] == 1
    assert "platform" in payload[0]["snippet"]


def test_get_thread_detail_returns_messages_and_linkage(client, auth_headers, db):
    mailbox = _create_mailbox(db, email="team@messages-example.com")
    contact = Contact(email="contact@example.com", first_name="Test")
    db.add(contact)
    db.flush()

    thread = Thread(
        mailbox_id=mailbox.id,
        external_thread_id="thread-2",
        subject="Follow up",
        participants=["contact@example.com", mailbox.email],
        contact_email="contact@example.com",
        contact_id=contact.id,
        linkage_status="linked",
        last_message_at=datetime.now(timezone.utc),
    )
    db.add(thread)
    db.flush()

    first_message = Message(
        id=uuid.uuid4(),
        thread_id=thread.id,
        mailbox_id=mailbox.id,
        direction="outbound",
        from_email=mailbox.email,
        to_emails=["contact@example.com"],
        subject="First touch",
        text_body="Checking in.",
        is_read=True,
        sent_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    second_message = Message(
        id=uuid.uuid4(),
        thread_id=thread.id,
        mailbox_id=mailbox.id,
        direction="inbound",
        from_email="contact@example.com",
        to_emails=[mailbox.email],
        subject="Re: First touch",
        text_body="Let's talk tomorrow.",
        is_read=False,
        received_at=datetime.now(timezone.utc),
    )
    db.add_all([first_message, second_message])
    db.commit()

    response = client.get(f"/api/v1/inbox/threads/{thread.id}", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(thread.id)
    assert payload["linkage_status"] == "linked"
    assert len(payload["messages"]) == 2
    assert payload["messages"][1]["direction"] == "inbound"
    assert payload["messages"][1]["body_text"] == "Let's talk tomorrow."


def test_inbox_status_explains_never_synced_state(client, auth_headers, db):
    _create_mailbox(db)
    response = client.get("/api/v1/inbox/status", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["configured_mailboxes_count"] == 1
    assert any(blocker["code"] == "never_synced" for blocker in payload["blockers"])


def test_manual_sync_uses_send_log_headers_to_thread_replies(client, auth_headers, db, monkeypatch):
    mailbox = _create_mailbox(db, email="reply@synced-example.com")
    contact = Contact(email="buyer@example.com", first_name="Buyer")
    db.add(contact)
    db.flush()

    send_log = SendLog(
        mailbox_id=mailbox.id,
        contact_id=contact.id,
        target_email=contact.email,
        subject="Intro outreach",
        delivery_status="success",
        provider_message_id="<sent-1@example.com>",
    )
    db.add(send_log)
    db.commit()

    raw_email = (
        b"From: buyer@example.com\r\n"
        b"To: reply@synced-example.com\r\n"
        b"Subject: Re: Intro outreach\r\n"
        b"Message-ID: <reply-1@example.com>\r\n"
        b"In-Reply-To: <sent-1@example.com>\r\n"
        b"Date: Tue, 14 Apr 2026 12:00:00 +0000\r\n"
        b"\r\n"
        b"I am interested.\r\n"
    )

    fetched = [
        type(
            "Fetched",
            (),
            {"uid": "10", "raw_bytes": raw_email, "is_read": False, "received_at": datetime.now(timezone.utc)},
        )()
    ]
    monkeypatch.setattr(
        "app.services.imap_service.MailcowIMAPProvider.fetch_messages",
        lambda self, host, port, username, password, since_uid=None: fetched,
    )

    response = client.post("/api/v1/inbox/sync", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["mailboxes_processed"] == 1
    assert payload["results"][0]["imported_count"] == 1

    threads_response = client.get("/api/v1/inbox/threads", headers=auth_headers)
    assert threads_response.status_code == 200
    threads = threads_response.json()
    assert len(threads) == 1
    assert threads[0]["contact_email"] == "buyer@example.com"
    assert threads[0]["linkage_status"] == "linked"


def test_list_thread_messages_returns_404_for_unknown_thread(client, auth_headers):
    response = client.get(
        f"/api/v1/inbox/threads/{uuid.uuid4()}",
        headers=auth_headers,
    )

    assert response.status_code == 404
