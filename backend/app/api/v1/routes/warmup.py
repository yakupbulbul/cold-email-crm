from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.core import Mailbox
from app.models.monitoring import JobLog
from app.models.warmup import WarmupEvent, WarmupPair
from app.schemas.warmup import WarmupControlRequest
from app.services.warmup_service import WarmupPlanner
from app.workers.warmup_worker import run_warmup_cycle

router = APIRouter()


def _queue_job_log(db: Session, *, job_type: str, payload_summary: dict, force_send: bool = False) -> str | None:
    try:
        task = run_warmup_cycle.delay(force_send=force_send)
    except Exception:
        return None

    job = JobLog(
        job_id=task.id,
        job_type=job_type,
        status="queued",
        payload_summary=payload_summary,
    )
    db.add(job)
    db.commit()
    return task.id

@router.post("/start")
def start_warmup(req: WarmupControlRequest, db: Session = Depends(get_db)):
    if not settings.BACKGROUND_WORKERS_ENABLED:
        raise HTTPException(
            status_code=409,
            detail="Background workers are disabled in low-RAM mode. Run make dev or make dev-full before starting warmup.",
        )

    mailbox = db.query(Mailbox).filter(Mailbox.id == req.mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    peers = (
        db.query(Mailbox)
        .filter(
            Mailbox.id != mailbox.id,
            Mailbox.status == "active",
        )
        .all()
    )
    if not peers:
        raise HTTPException(
            status_code=409,
            detail="Warm-up requires at least one other active local mailbox before it can start.",
        )

    mailbox.warmup_enabled = True
    created_pairs = 0
    reactivated_pairs = 0

    for peer in peers:
        pair = (
            db.query(WarmupPair)
            .filter(
                WarmupPair.sender_mailbox_id == mailbox.id,
                WarmupPair.recipient_mailbox_id == peer.id,
            )
            .first()
        )
        if pair:
            if not pair.is_active:
                pair.is_active = True
                reactivated_pairs += 1
        else:
            db.add(
                WarmupPair(
                    sender_mailbox_id=mailbox.id,
                    recipient_mailbox_id=peer.id,
                    is_active=True,
                )
            )
            created_pairs += 1

    db.commit()
    job_id = _queue_job_log(
        db,
        job_type="warmup_cycle",
        payload_summary={
            "mailbox_id": str(mailbox.id),
            "created_pairs": created_pairs,
            "reactivated_pairs": reactivated_pairs,
        },
        force_send=True,
    )
    return {
        "status": "started",
        "mailbox_id": str(mailbox.id),
        "active_pair_count": created_pairs + reactivated_pairs,
        "job_queued": bool(job_id),
        "job_id": job_id,
        "detail": "Warm-up enabled for this mailbox." if created_pairs + reactivated_pairs else "Warm-up was already enabled for all available peers.",
    }

@router.post("/stop")
def stop_warmup(req: WarmupControlRequest, db: Session = Depends(get_db)):
    if not settings.BACKGROUND_WORKERS_ENABLED:
        raise HTTPException(
            status_code=409,
            detail="Background workers are disabled in low-RAM mode. Run make dev or make dev-full before stopping warmup.",
        )

    mailbox = db.query(Mailbox).filter(Mailbox.id == req.mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")

    mailbox.warmup_enabled = False
    deactivated_pairs = (
        db.query(WarmupPair)
        .filter(
            WarmupPair.is_active == True,
            or_(WarmupPair.sender_mailbox_id == mailbox.id, WarmupPair.recipient_mailbox_id == mailbox.id),
        )
        .all()
    )
    for pair in deactivated_pairs:
        pair.is_active = False
    db.commit()
    return {
        "status": "stopped",
        "mailbox_id": str(mailbox.id),
        "deactivated_pairs": len(deactivated_pairs),
    }

@router.get("/status")
def get_warmup_status(db: Session = Depends(get_db)):
    active_pairs = db.query(WarmupPair).filter(WarmupPair.is_active == True).all()
    today = datetime.utcnow().date()

    pair_rows = []
    successful_sends = 0
    for pair in active_pairs:
        sent_today = (
            db.query(func.count())
            .select_from(WarmupEvent)
            .filter(
                WarmupEvent.mailbox_id == pair.sender_mailbox_id,
                WarmupEvent.event_type == "send",
                WarmupEvent.status == "success",
                WarmupEvent.created_at >= today,
            )
            .scalar()
        )
        successful_sends += sent_today or 0
        pair_rows.append(
            {
                "id": str(pair.id),
                "mailbox_id": str(pair.sender_mailbox_id),
                "mailbox_a": pair.sender.email,
                "mailbox_b": pair.recipient.email,
                "is_active": pair.is_active,
                "sent": sent_today or 0,
                "limit": WarmupPlanner.get_daily_limit(pair.sender),
                "updated_at": pair.updated_at.isoformat() if pair.updated_at else None,
            }
        )

    total_capacity = sum(max(pair["limit"], 1) for pair in pair_rows)
    global_health = int((successful_sends / total_capacity) * 100) if total_capacity else 0
    enabled_mailboxes = db.query(Mailbox).filter(Mailbox.warmup_enabled == True).count()

    return {
        "workers_enabled": settings.BACKGROUND_WORKERS_ENABLED,
        "warming_mailboxes": enabled_mailboxes,
        "active_pairs": pair_rows,
        "total_sent": successful_sends,
        "global_health": global_health,
    }

@router.get("/events")
def get_warmup_events(db: Session = Depends(get_db)):
    from app.models.warmup import WarmupEvent

    events = (
        db.query(WarmupEvent)
        .order_by(WarmupEvent.created_at.desc())
        .limit(100)
        .all()
    )
    return events
