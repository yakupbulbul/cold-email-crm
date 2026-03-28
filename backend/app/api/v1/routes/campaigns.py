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
