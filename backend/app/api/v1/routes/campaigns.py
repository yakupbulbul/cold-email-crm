from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.models.campaign import Campaign

router = APIRouter()

@router.post("/", response_model=CampaignResponse)
def create_campaign(req: CampaignCreate, db: Session = Depends(get_db)):
    c = Campaign(
        name=req.name,
        mailbox_id=req.mailbox_id,
        template_subject=req.template_subject,
        template_body=req.template_body,
        daily_limit=req.daily_limit
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

@router.post("/{campaign_id}/start")
def start_campaign(campaign_id: str, db: Session = Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    c.status = "active"
    db.commit()
    return {"status": "started", "campaign": c.name}
    
@router.post("/{campaign_id}/pause")
def pause_campaign(campaign_id: str, db: Session = Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    c.status = "paused"
    db.commit()
    return {"status": "paused"}

@router.get("/{campaign_id}/lead-quality")
def lead_quality_report(campaign_id: str, db: Session = Depends(get_db)):
    from app.models.campaign import CampaignLead, Contact
    leads = db.query(Contact).join(CampaignLead).filter(CampaignLead.campaign_id == campaign_id).all()
    
    valid = sum(1 for c in leads if c.verification_score == 100)
    risky = sum(1 for c in leads if c.verification_score >= 80 and c.verification_score < 100)
    invalid = sum(1 for c in leads if c.verification_score < 80)
    suppressed = sum(1 for c in leads if c.is_suppressed)
    
    return {
        "valid": valid,
        "risky": risky,
        "invalid": invalid,
        "suppressed": suppressed,
        "total": len(leads)
    }

@router.post("/{campaign_id}/preflight")
def campaign_preflight_clean(campaign_id: str, db: Session = Depends(get_db)):
    from app.models.campaign import CampaignLead, Contact
    
    campaign_leads = db.query(CampaignLead).join(Contact).filter(
        CampaignLead.campaign_id == campaign_id,
        CampaignLead.status == "scheduled",
        (Contact.is_suppressed == True) | (Contact.verification_score < 80)
    ).all()
    
    cleaned = 0
    for cl in campaign_leads:
        cl.status = "failed"
        cleaned += 1
        
    db.commit()
    return {"status": "preflight_complete", "removed_from_queue": cleaned}
