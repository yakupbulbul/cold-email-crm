from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.email import Message, Thread

router = APIRouter()


@router.get("/threads")
def list_threads(db: Session = Depends(get_db)):
    threads = (
        db.query(Thread)
        .options(joinedload(Thread.messages))
        .order_by(Thread.last_message_at.desc())
        .all()
    )

    payload = []
    for thread in threads:
        ordered_messages = sorted(
            thread.messages,
            key=lambda item: item.received_at or item.sent_at or item.created_at,
            reverse=True,
        )
        latest_message = ordered_messages[0] if ordered_messages else None
        contact_email = ""
        if latest_message:
            contact_email = latest_message.from_email if latest_message.direction == "inbound" else (
                latest_message.to_emails[0] if latest_message.to_emails else ""
            )

        payload.append(
            {
                "id": str(thread.id),
                "subject": thread.subject or "",
                "contact_email": contact_email,
                "contact_name": None,
                "status": "active",
                "last_message_at": (thread.last_message_at or thread.created_at).isoformat(),
                "snippet": (
                    (latest_message.text_body or latest_message.subject or "")[:160]
                    if latest_message
                    else ""
                ),
                "unread": bool(latest_message and latest_message.direction == "inbound"),
            }
        )

    return payload


@router.get("/threads/{thread_id}/messages")
def list_thread_messages(thread_id: UUID, db: Session = Depends(get_db)):
    thread = (
        db.query(Thread)
        .options(joinedload(Thread.messages))
        .filter(Thread.id == thread_id)
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    ordered_messages = sorted(
        thread.messages,
        key=lambda item: item.received_at or item.sent_at or item.created_at,
    )
    return [
        {
            "id": str(message.id),
            "thread_id": str(message.thread_id),
            "direction": message.direction,
            "subject": message.subject or "",
            "body_text": message.text_body or "",
            "body_html": message.html_body,
            "from_address": message.from_email,
            "to_address": ", ".join(message.to_emails or []),
            "sent_at": (
                message.sent_at or message.received_at or message.created_at
            ).isoformat(),
        }
        for message in ordered_messages
    ]
