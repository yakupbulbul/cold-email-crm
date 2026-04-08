from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.campaign import Campaign, CampaignLead, Contact
from app.models.monitoring import JobLog
from app.schemas.campaign import CampaignCreate, CampaignResponse
from app.services.verification_service import contact_is_reachable
from app.workers.campaign_worker import run_campaign_cycle

router = APIRouter()

@router.get("/")
@router.get("")  # Handle both /campaigns and /campaigns/ without redirect
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).all()

@router.post("/", response_model=CampaignResponse)
@router.post("")  # Handle both /campaigns and /campaigns/ without redirect
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
    if not settings.BACKGROUND_WORKERS_ENABLED:
        raise HTTPException(
            status_code=409,
            detail="Background workers are disabled in lean development mode. Run make dev-full before starting campaigns.",
        )

    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")

    scheduled_leads = (
        db.query(CampaignLead)
        .join(Contact)
        .filter(
            CampaignLead.campaign_id == campaign_id,
            CampaignLead.status == "scheduled",
        )
        .all()
    )
    eligible_leads = sum(1 for lead in scheduled_leads if contact_is_reachable(lead.contact))
    if eligible_leads == 0:
        raise HTTPException(
            status_code=409,
            detail="Campaign cannot start until it has at least one scheduled, verified, unsuppressed lead.",
        )

    c.status = "active"
    db.commit()
    job_id = None
    try:
        task = run_campaign_cycle.delay()
        job_id = task.id
        db.add(
            JobLog(
                job_id=task.id,
                job_type="campaign_cycle",
                status="queued",
                payload_summary={
                    "campaign_id": str(c.id),
                    "campaign_name": c.name,
                    "eligible_leads": eligible_leads,
                },
            )
        )
        db.commit()
    except Exception:
        job_id = None

    return {
        "status": "started",
        "campaign": c.name,
        "eligible_leads": eligible_leads,
        "job_queued": bool(job_id),
        "job_id": job_id,
    }
    
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
    
    valid = sum(1 for c in leads if c.email_status == "valid")
    risky = sum(1 for c in leads if c.email_status == "risky")
    invalid = sum(1 for c in leads if c.email_status not in {"valid", "risky"})
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
    ).all()
    leads = [lead for lead in leads if contact_is_reachable(lead)]
    
    from fastapi.responses import StreamingResponse
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Email", "First Name", "Last Name", "Company"])
    for c in leads:
        writer.writerow([c.email, c.first_name, c.last_name, c.company])
    output.seek(0)
    return StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8')), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=campaign_ready_leads.csv"})
