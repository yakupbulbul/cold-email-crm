from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.models.campaign import Campaign

router = APIRouter()

@router.get("/")
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).all()

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

@router.get("/{campaign_id}/preflight/history")
def get_preflight_history(campaign_id: str, db: Session = Depends(get_db)):
    from app.models.monitoring import CampaignPreflightCheck
    checks = db.query(CampaignPreflightCheck).filter(CampaignPreflightCheck.campaign_id == campaign_id).order_by(CampaignPreflightCheck.created_at.desc()).limit(50).all()
    return checks

@router.post("/{campaign_id}/preflight")
def campaign_preflight_evaluation(campaign_id: str, db: Session = Depends(get_db)):
    from app.services.preflight_service import PreflightService
    svc = PreflightService(db)
    result = svc.run_preflight(campaign_id)
    return result
    # Replaced by robust Domain Resolvers

@router.get("/{campaign_id}/export-ready-leads")
def export_ready_campaign_leads(campaign_id: str, db: Session = Depends(get_db)):
    from app.models.campaign import CampaignLead, Contact
    leads = db.query(Contact).join(CampaignLead).filter(
        CampaignLead.campaign_id == campaign_id,
        CampaignLead.status == "scheduled",
        Contact.is_suppressed == False,
        Contact.verification_score >= 80
    ).all()
    
    from fastapi.responses import StreamingResponse
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Email", "First Name", "Last Name", "Company"])
    for c in leads:
        writer.writerow([c.email, c.first_name, c.last_name, c.company])
    output.seek(0)
    return StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8')), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=campaign_ready_leads.csv"})
