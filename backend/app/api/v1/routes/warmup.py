from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.schemas.warmup import WarmupControlRequest, WarmupStatusResponse
from app.models.core import Mailbox
from app.models.warmup import WarmupPair
import uuid

router = APIRouter()

@router.post("/start")
def start_warmup(req: WarmupControlRequest, db: Session = Depends(get_db)):
    if not settings.BACKGROUND_WORKERS_ENABLED:
        raise HTTPException(
            status_code=409,
            detail="Background workers are disabled in lean development mode. Run make dev-full before starting warmup.",
        )

    mailbox = db.query(Mailbox).filter(Mailbox.id == req.mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
        
    mailbox.warmup_enabled = True
    db.commit()
    return {"status": "Warm-up started"}

@router.post("/stop")
def stop_warmup(req: WarmupControlRequest, db: Session = Depends(get_db)):
    if not settings.BACKGROUND_WORKERS_ENABLED:
        raise HTTPException(
            status_code=409,
            detail="Background workers are disabled in lean development mode. Run make dev-full before stopping warmup.",
        )

    mailbox = db.query(Mailbox).filter(Mailbox.id == req.mailbox_id).first()
    if not mailbox:
        raise HTTPException(status_code=404, detail="Mailbox not found")
        
    mailbox.warmup_enabled = False
    db.commit()
    return {"status": "Warm-up stopped"}

@router.get("/status", response_model=list[WarmupStatusResponse])
def get_warmup_status(db: Session = Depends(get_db)):
    # Mocking aggregated status
    return []

@router.get("/events")
def get_warmup_events(db: Session = Depends(get_db)):
    return []
