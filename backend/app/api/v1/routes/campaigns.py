from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.campaign import Campaign, CampaignLead, Contact
from app.models.lists import CampaignList
from app.models.monitoring import JobLog
from app.schemas.campaign import CampaignCreate, CampaignResponse, CampaignUpdate
from app.schemas.lists import CampaignListAttachPayload
from app.services.list_service import LeadListService
from app.services.verification_service import contact_is_reachable
from app.workers.campaign_worker import run_campaign_cycle

router = APIRouter()


def _campaign_payload(db: Session, campaign: Campaign) -> dict:
    service = LeadListService(db)
    campaign_lists_summary = service.summarize_campaign_lists(str(campaign.id))
    sent_count = db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign.id, CampaignLead.status == "sent").count()
    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "status": campaign.status,
        "mailbox_id": str(campaign.mailbox_id) if campaign.mailbox_id else None,
        "template_subject": campaign.template_subject,
        "template_body": campaign.template_body,
        "daily_limit": campaign.daily_limit,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "lead_count": campaign_lists_summary["lead_count"],
        "sent_count": sent_count,
        "reply_rate": "0%",
        "lists_summary": campaign_lists_summary,
    }

@router.get("/")
@router.get("")  # Handle both /campaigns and /campaigns/ without redirect
def list_campaigns(db: Session = Depends(get_db)):
    return [_campaign_payload(db, campaign) for campaign in db.query(Campaign).all()]

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
    return _campaign_payload(db, c)


@router.put("/{campaign_id}")
def update_campaign(campaign_id: str, req: CampaignUpdate, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.name = req.name
    campaign.mailbox_id = req.mailbox_id
    campaign.template_subject = req.template_subject
    campaign.template_body = req.template_body
    campaign.daily_limit = req.daily_limit
    db.commit()
    db.refresh(campaign)
    return _campaign_payload(db, campaign)


@router.post("/{campaign_id}/lists")
def attach_list_to_campaign(campaign_id: str, req: CampaignListAttachPayload, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    service = LeadListService(db)
    lead_list = service.get_list_or_404(str(req.list_id))
    existing = db.query(CampaignList).filter(CampaignList.campaign_id == campaign.id, CampaignList.list_id == lead_list.id).first()
    if not existing:
        db.add(CampaignList(campaign_id=campaign.id, list_id=lead_list.id))
        db.commit()
    return service.sync_campaign_leads(campaign_id)


@router.get("/{campaign_id}/lists")
def get_campaign_lists(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    service = LeadListService(db)
    return service.summarize_campaign_lists(campaign_id)


@router.delete("/{campaign_id}/lists/{list_id}")
def remove_list_from_campaign(campaign_id: str, list_id: str, db: Session = Depends(get_db)):
    attached = db.query(CampaignList).filter(CampaignList.campaign_id == campaign_id, CampaignList.list_id == list_id).first()
    if not attached:
        raise HTTPException(status_code=404, detail="List is not attached to this campaign")
    db.delete(attached)
    db.commit()
    service = LeadListService(db)
    return service.sync_campaign_leads(campaign_id)

@router.post("/{campaign_id}/start")
def start_campaign(campaign_id: str, db: Session = Depends(get_db)):
    if not settings.BACKGROUND_WORKERS_ENABLED:
        raise HTTPException(
            status_code=409,
            detail="Background workers are disabled in low-RAM mode. Run make dev or make dev-full before starting campaigns.",
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
