from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.monitoring import JobLog
from app.schemas.warmup import WarmupGlobalActionResponse
from app.services.warmup_service import WarmupService
from app.workers.warmup_worker import run_warmup_cycle

router = APIRouter()


def _queue_job_log(db: Session, *, payload_summary: dict, force_send: bool = False) -> str | None:
    try:
        task = run_warmup_cycle.delay(force_send=force_send)
    except Exception:
        return None

    job = JobLog(
        job_id=task.id,
        job_type="warmup_cycle",
        status="queued",
        payload_summary=payload_summary,
    )
    db.add(job)
    db.commit()
    return task.id


@router.post("/start", response_model=WarmupGlobalActionResponse)
def start_warmup(db: Session = Depends(get_db)):
    if not settings.BACKGROUND_WORKERS_ENABLED:
        raise HTTPException(
            status_code=409,
            detail="Background workers are disabled in low-RAM mode. Run make dev or make dev-full before starting warmup.",
        )

    service = WarmupService(db)
    service.set_global_enabled(True)
    status = service.get_status_payload()

    job_id = None
    detail = "Warm-up enabled globally."
    if status["eligible_mailboxes_count"] >= 2:
        job_id = _queue_job_log(
            db,
            payload_summary={
                "action": "global_start",
                "eligible_mailboxes_count": status["eligible_mailboxes_count"],
                "active_pairs_count": status["active_pairs_count"],
            },
            force_send=True,
        )
        detail = "Warm-up enabled globally and an immediate warm-up cycle was queued." if job_id else "Warm-up enabled globally, but the immediate warm-up cycle could not be queued."
    elif status["blockers"]:
        detail = status["blockers"][0]["message"]

    return {
        "status": "enabled",
        "detail": detail,
        "job_queued": bool(job_id),
        "job_id": job_id,
    }


@router.post("/pause", response_model=WarmupGlobalActionResponse)
def pause_warmup(db: Session = Depends(get_db)):
    service = WarmupService(db)
    service.set_global_enabled(False)
    return {
        "status": "paused",
        "detail": "Warm-up paused globally. Active pairs remain configured but will not be processed until warm-up is started again.",
        "job_queued": False,
        "job_id": None,
    }


@router.post("/stop", response_model=WarmupGlobalActionResponse)
def stop_warmup(db: Session = Depends(get_db)):
    return pause_warmup(db)


@router.get("/status")
def get_warmup_status(db: Session = Depends(get_db)):
    return WarmupService(db).get_status_payload()


@router.get("/pairs")
def get_warmup_pairs(db: Session = Depends(get_db)):
    return WarmupService(db).get_pairs_payload()


@router.get("/logs")
def get_warmup_logs(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    return WarmupService(db).get_logs_payload(limit=limit)


@router.get("/events")
def get_warmup_events(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)):
    return WarmupService(db).get_logs_payload(limit=limit)
