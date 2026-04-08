from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.monitoring import DeliverabilityEvent
from app.models.campaign import Campaign, Contact
from app.models.core import Mailbox, Domain
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=30)
    events = db.query(DeliverabilityEvent.event_type, func.count(DeliverabilityEvent.id))\
        .filter(DeliverabilityEvent.occurred_at >= cutoff)\
        .group_by(DeliverabilityEvent.event_type).all()
        
    res = {"sent": 0, "replied": 0, "bounced": 0, "suppressed": 0}
    for k, v in events:
        if k in res:
            res[k] = v
    res.update({
        "total_contacts": db.query(func.count(Contact.id)).scalar() or 0,
        "valid_contacts": db.query(func.count(Contact.id)).filter(Contact.email_status == "valid").scalar() or 0,
        "risky_contacts": db.query(func.count(Contact.id)).filter(Contact.email_status == "risky").scalar() or 0,
        "invalid_contacts": db.query(func.count(Contact.id)).filter(Contact.email_status.in_(["invalid", "no_mx", "disposable", "role_based", "duplicate"])).scalar() or 0,
        "suppressed_contacts": db.query(func.count(Contact.id)).filter(Contact.is_suppressed == True).scalar() or 0,
        "unsubscribed_contacts": db.query(func.count(Contact.id)).filter(Contact.unsubscribe_status.in_(["unsubscribed", "suppressed"])).scalar() or 0,
        "b2b_campaigns": db.query(func.count(Campaign.id)).filter(Campaign.campaign_type == "b2b").scalar() or 0,
        "b2c_campaigns": db.query(func.count(Campaign.id)).filter(Campaign.campaign_type == "b2c").scalar() or 0,
        "active_campaigns": db.query(func.count(Campaign.id)).filter(Campaign.status == "active").scalar() or 0,
        "mailbox_count": db.query(func.count(Mailbox.id)).scalar() or 0,
        "domain_count": db.query(func.count(Domain.id)).scalar() or 0,
    })
    return res

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
    # Very basic aggregation by mailbox
    res = db.query(
        Mailbox.email,
        DeliverabilityEvent.event_type,
        func.count(DeliverabilityEvent.id)
    ).join(Mailbox, DeliverabilityEvent.mailbox_id == Mailbox.id)\
     .group_by(Mailbox.email, DeliverabilityEvent.event_type).all()
     
    boxes = {}
    for email, kind, count in res:
        if email not in boxes:
            boxes[email] = {"sent": 0, "bounced": 0, "replied": 0}
        if kind in boxes[email]:
            boxes[email][kind] = count
            
    return [{"mailbox": k, **v} for k,v in boxes.items()]
