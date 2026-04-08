"""test_inbox.py — Inbox endpoint tests."""
import uuid
from datetime import datetime, timedelta

from app.models.core import Domain, Mailbox
from app.models.email import Message, Thread


def test_list_threads_returns_latest_snippet_and_unread(client, auth_headers, db):
    domain = Domain(name="inbox-example.com")
    db.add(domain)
    db.flush()

    mailbox = Mailbox(
        domain_id=domain.id,
        email="sales@inbox-example.com",
        display_name="Sales",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="sales@inbox-example.com",
        smtp_password_encrypted="encrypted",
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="sales@inbox-example.com",
        imap_password_encrypted="encrypted",
    )
    db.add(mailbox)
    db.flush()

    thread = Thread(
        mailbox_id=mailbox.id,
        external_thread_id="thread-1",
        subject="Interested in a demo",
        participants=["buyer@example.com", mailbox.email],
        last_message_at=datetime.utcnow(),
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
                sent_at=datetime.utcnow() - timedelta(hours=2),
            ),
            Message(
                thread_id=thread.id,
                mailbox_id=mailbox.id,
                direction="inbound",
                from_email="buyer@example.com",
                to_emails=[mailbox.email],
                subject="Interested in a demo",
                text_body="Can you show me the platform this week?",
                received_at=datetime.utcnow() - timedelta(hours=1),
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
    assert "platform" in payload[0]["snippet"]


def test_list_thread_messages_returns_messages_in_chronological_order(client, auth_headers, db):
    domain = Domain(name="messages-example.com")
    db.add(domain)
    db.flush()

    mailbox = Mailbox(
        domain_id=domain.id,
        email="team@messages-example.com",
        display_name="Team",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="team@messages-example.com",
        smtp_password_encrypted="encrypted",
        imap_host="imap.example.com",
        imap_port=993,
        imap_username="team@messages-example.com",
        imap_password_encrypted="encrypted",
    )
    db.add(mailbox)
    db.flush()

    thread = Thread(
        mailbox_id=mailbox.id,
        external_thread_id="thread-2",
        subject="Follow up",
        participants=["contact@example.com", mailbox.email],
        last_message_at=datetime.utcnow(),
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
        sent_at=datetime.utcnow() - timedelta(days=1),
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
        received_at=datetime.utcnow(),
    )
    db.add_all([first_message, second_message])
    db.commit()

    response = client.get(f"/api/v1/inbox/threads/{thread.id}/messages", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [str(first_message.id), str(second_message.id)]
    assert payload[1]["direction"] == "inbound"
    assert payload[1]["body_text"] == "Let's talk tomorrow."


def test_list_thread_messages_returns_404_for_unknown_thread(client, auth_headers):
    response = client.get(
        f"/api/v1/inbox/threads/{uuid.uuid4()}/messages",
        headers=auth_headers,
    )

    assert response.status_code == 404
