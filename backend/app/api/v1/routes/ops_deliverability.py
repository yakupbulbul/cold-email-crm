from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.monitoring import DeliverabilityEvent
from app.services.deliverability_service import DeliverabilityService
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    return DeliverabilityService(db).legacy_summary()

@router.get("/trends")
def get_trends(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=7)
    # Generic grouping by date
    events = db.query(
        func.date(DeliverabilityEvent.occurred_at).label("date"),
        DeliverabilityEvent.event_type,
        func.count(DeliverabilityEvent.id).label("count")
    ).filter(DeliverabilityEvent.occurred_at >= cutoff)\
     .group_by(func.date(DeliverabilityEvent.occurred_at), DeliverabilityEvent.event_type).all()
     
    trend_dict = {}
    for ev in events:
        date_str = str(ev.date)
        if date_str not in trend_dict:
            trend_dict[date_str] = {"sent": 0, "bounced": 0, "replied": 0, "suppressed": 0}
        
        kind = ev.event_type
        if kind in trend_dict[date_str]:
            trend_dict[date_str][kind] = ev.count
            
    # Format for rechart
    result = [{"date": k, **v} for k, v in sorted(trend_dict.items())]
    return result

@router.get("/mailboxes")
def get_mailbox_stats(db: Session = Depends(get_db)):
    return DeliverabilityService(db).legacy_mailbox_stats()
