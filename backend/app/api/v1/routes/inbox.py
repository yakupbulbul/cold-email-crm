from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.models.core import Mailbox
from app.models.email import Message, Thread
from app.models.monitoring import JobLog, WorkerHeartbeat
from app.services.imap_service import (
    IMAPSyncManager,
    build_inbox_message_payload,
    build_inbox_thread_summary,
    infer_inbox_blockers,
)
from app.workers.imap_sync_worker import sync_all_inboxes

router = APIRouter()


def _serialize_mailbox_sync(mailbox: Mailbox) -> dict:
    return {
        "id": str(mailbox.id),
        "email": mailbox.email,
        "display_name": mailbox.display_name,
        "status": mailbox.status,
        "inbox_sync_enabled": mailbox.inbox_sync_enabled,
        "inbox_sync_status": mailbox.inbox_sync_status or "unknown",
        "inbox_last_synced_at": mailbox.inbox_last_synced_at.isoformat() if mailbox.inbox_last_synced_at else None,
        "inbox_last_success_at": mailbox.inbox_last_success_at.isoformat() if mailbox.inbox_last_success_at else None,
        "inbox_last_error": mailbox.inbox_last_error,
        "smtp_last_check_status": mailbox.smtp_last_check_status,
        "imap_host": mailbox.imap_host,
        "imap_port": mailbox.imap_port,
    }


def _worker_status(db: Session) -> dict:
    latest_heartbeat = (
        db.query(WorkerHeartbeat)
        .filter(WorkerHeartbeat.worker_type == "pipeline")
        .order_by(WorkerHeartbeat.last_seen_at.desc())
        .first()
    )
    if latest_heartbeat is None:
        return {
            "status": "disabled" if not settings.BACKGROUND_WORKERS_ENABLED else "unknown",
            "detail": "Background workers are disabled." if not settings.BACKGROUND_WORKERS_ENABLED else "No worker heartbeat recorded yet.",
            "last_seen_at": None,
        }
    stale = latest_heartbeat.last_seen_at < datetime.utcnow() - timedelta(minutes=2)
    return {
        "status": "healthy" if not stale else "stale",
        "detail": "Background workers are running." if not stale else "Worker heartbeat is stale.",
        "last_seen_at": latest_heartbeat.last_seen_at.isoformat(),
    }


def _scheduler_status(db: Session) -> dict:
    latest_sync_job = (
        db.query(JobLog)
        .filter(JobLog.job_type == "imap_sync")
        .order_by(JobLog.created_at.desc())
        .first()
    )
    if latest_sync_job is None:
        return {
            "status": "disabled" if not settings.BACKGROUND_IMAP_SYNC_ENABLED else "never_run",
            "detail": "Automatic inbox sync is disabled." if not settings.BACKGROUND_IMAP_SYNC_ENABLED else "Inbox sync has never been scheduled.",
            "last_seen_at": None,
            "next_run_at": None,
        }
    stale_cutoff = datetime.utcnow() - timedelta(minutes=3)
    status = "healthy" if latest_sync_job.created_at >= stale_cutoff else "stale"
    next_run_at = latest_sync_job.created_at + timedelta(minutes=1)
    return {
        "status": status,
        "detail": "Automatic inbox sync is running." if status == "healthy" else "Inbox sync scheduler has not enqueued a recent sync job.",
        "last_seen_at": latest_sync_job.created_at.isoformat(),
        "next_run_at": next_run_at.isoformat(),
    }


@router.get("/status")
def get_inbox_status(db: Session = Depends(get_db)):
    mailboxes = db.query(Mailbox).order_by(Mailbox.created_at.asc()).all()
    threads_count = db.query(Thread).count()
    successful_sends_today = db.query(Message).filter(
        Message.direction == "inbound",
        Message.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
    ).count()
    latest_thread = db.query(Thread).order_by(Thread.last_message_at.desc()).first()
    blockers = infer_inbox_blockers(
        mailboxes=mailboxes,
        threads_count=threads_count,
        workers_enabled=settings.BACKGROUND_WORKERS_ENABLED,
        auto_sync_enabled=settings.BACKGROUND_IMAP_SYNC_ENABLED,
    )
    return {
        "sync_enabled": settings.BACKGROUND_IMAP_SYNC_ENABLED,
        "workers_enabled": settings.BACKGROUND_WORKERS_ENABLED,
        "worker_status": _worker_status(db),
        "scheduler_status": _scheduler_status(db),
        "mailboxes": [_serialize_mailbox_sync(mailbox) for mailbox in mailboxes],
        "configured_mailboxes_count": len(mailboxes),
        "sync_enabled_mailboxes_count": len([mailbox for mailbox in mailboxes if mailbox.inbox_sync_enabled]),
        "healthy_mailboxes_count": len([mailbox for mailbox in mailboxes if mailbox.inbox_sync_status == "healthy"]),
        "threads_count": threads_count,
        "unread_threads_count": len(
            [
                thread
                for thread in db.query(Thread).options(joinedload(Thread.messages)).all()
                if any(message.direction == "inbound" and not message.is_read for message in thread.messages)
            ]
        ),
        "messages_received_today": successful_sends_today,
        "last_sync_at": max(
            [mailbox.inbox_last_synced_at for mailbox in mailboxes if mailbox.inbox_last_synced_at],
            default=None,
        ).isoformat() if any(mailbox.inbox_last_synced_at for mailbox in mailboxes) else None,
        "last_message_at": latest_thread.last_message_at.isoformat() if latest_thread and latest_thread.last_message_at else None,
        "blockers": blockers,
    }


@router.post("/sync")
def sync_inbox(mailbox_id: UUID | None = None, db: Session = Depends(get_db)):
    manager = IMAPSyncManager(db)
    if mailbox_id is not None:
        outcome = manager.sync_mailbox(mailbox_id)
        return {
            "status": "completed" if outcome.status == "healthy" else outcome.status,
            "mailboxes_processed": 1,
            "results": [outcome.__dict__],
        }

    mailboxes = (
        db.query(Mailbox)
        .filter(Mailbox.status == "active", Mailbox.inbox_sync_enabled.is_(True))
        .order_by(Mailbox.created_at.asc())
        .all()
    )
    results = [manager.sync_mailbox(mailbox.id).__dict__ for mailbox in mailboxes]
    return {
        "status": "completed",
        "mailboxes_processed": len(mailboxes),
        "results": results,
    }


@router.post("/enqueue-sync")
def enqueue_inbox_sync():
    if not settings.BACKGROUND_WORKERS_ENABLED:
        raise HTTPException(status_code=409, detail="Background workers are disabled, so automatic inbox sync cannot be queued.")
    async_result = sync_all_inboxes.delay()
    return {"status": "queued", "job_id": async_result.id}


@router.get("/threads")
def list_threads(
    mailbox_id: UUID | None = None,
    unread_only: bool = False,
    search: str | None = Query(default=None, min_length=1),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Thread)
        .options(
            joinedload(Thread.messages),
            joinedload(Thread.mailbox),
            joinedload(Thread.campaign),
            joinedload(Thread.contact),
        )
        .order_by(Thread.last_message_at.desc(), Thread.created_at.desc())
    )
    if mailbox_id is not None:
        query = query.filter(Thread.mailbox_id == mailbox_id)
    if search:
        normalized = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                Thread.subject.ilike(normalized),
                Thread.contact_email.ilike(normalized),
            )
        )

    threads = query.all()
    payload = [build_inbox_thread_summary(thread) for thread in threads]
    if unread_only:
        payload = [thread for thread in payload if thread["unread"]]
    return payload


@router.get("/threads/{thread_id}")
def get_thread_detail(thread_id: UUID, db: Session = Depends(get_db)):
    thread = (
        db.query(Thread)
        .options(
            joinedload(Thread.messages),
            joinedload(Thread.mailbox),
            joinedload(Thread.campaign),
            joinedload(Thread.contact),
        )
        .filter(Thread.id == thread_id)
        .first()
    )
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    summary = build_inbox_thread_summary(thread)
    summary["messages"] = [
        build_inbox_message_payload(message)
        for message in sorted(thread.messages, key=lambda item: item.received_at or item.sent_at or item.created_at)
    ]
    return summary


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
    return [build_inbox_message_payload(message) for message in ordered_messages]
