from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.database import get_db
from app.models.campaign import Campaign, CampaignLead, Contact
from app.models.lists import CampaignList
from app.models.monitoring import JobLog
from app.schemas.campaign import CampaignCreate, CampaignResponse, CampaignUpdate
from app.schemas.lists import CampaignListAttachPayload
from app.services.audience_service import evaluate_contact_for_campaign
from app.services.list_service import LeadListService
from app.workers.campaign_worker import run_campaign_cycle

router = APIRouter()
CAMPAIGN_BEAT_INTERVAL_SECONDS = 300


def _campaign_job_for_status(db: Session, campaign_id: str, statuses: set[str]) -> JobLog | None:
    for job in db.query(JobLog).filter(JobLog.job_type == "campaign_cycle").order_by(JobLog.created_at.desc()).all():
        payload_summary = job.payload_summary or {}
        if payload_summary.get("campaign_id") == campaign_id and job.status in statuses:
            return job
    return None


def _campaign_jobs_for_campaign(db: Session, campaign_id: str) -> list[JobLog]:
    matched: list[JobLog] = []
    for job in db.query(JobLog).filter(JobLog.job_type == "campaign_cycle").order_by(JobLog.created_at.desc()).all():
        payload_summary = job.payload_summary or {}
        if payload_summary.get("campaign_id") == campaign_id:
            matched.append(job)
    return matched


def _next_campaign_beat_at(now: datetime) -> datetime:
    interval_minutes = CAMPAIGN_BEAT_INTERVAL_SECONDS // 60
    next_boundary_minute = ((now.minute // interval_minutes) + 1) * interval_minutes
    if next_boundary_minute >= 60:
        return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return now.replace(minute=next_boundary_minute, second=0, microsecond=0)


def _campaign_execution_summary(db: Session, campaign: Campaign) -> dict:
    now = datetime.utcnow()
    jobs = _campaign_jobs_for_campaign(db, str(campaign.id))
    latest_job = jobs[0] if jobs else None
    latest_running = next((job for job in jobs if job.status == "running"), None)
    latest_completed = next((job for job in jobs if job.status == "completed"), None)
    latest_failed = next((job for job in jobs if job.status == "failed"), None)
    stale_after = now - timedelta(seconds=CAMPAIGN_BEAT_INTERVAL_SECONDS * 2)

    recent_queued = next(
        (
            job
            for job in jobs
            if job.status == "queued"
            and job.created_at
            and job.created_at >= stale_after
            and not (
                latest_completed
                and latest_completed.created_at
                and latest_completed.created_at >= job.created_at
            )
            and not (
                latest_failed
                and latest_failed.created_at
                and latest_failed.created_at >= job.created_at
            )
        ),
        None,
    )

    if latest_running:
        return {
            "state": "running",
            "job_id": latest_running.job_id,
            "job_created_at": latest_running.created_at.isoformat() if latest_running.created_at else None,
            "job_started_at": latest_running.started_at.isoformat() if latest_running.started_at else None,
            "last_completed_at": latest_completed.finished_at.isoformat() if latest_completed and latest_completed.finished_at else None,
            "next_dispatch_at": None,
            "beat_interval_seconds": CAMPAIGN_BEAT_INTERVAL_SECONDS,
            "detail": "A campaign worker is actively processing this campaign now.",
        }

    if recent_queued:
        return {
            "state": "queued",
            "job_id": recent_queued.job_id,
            "job_created_at": recent_queued.created_at.isoformat() if recent_queued.created_at else None,
            "job_started_at": recent_queued.started_at.isoformat() if recent_queued.started_at else None,
            "last_completed_at": latest_completed.finished_at.isoformat() if latest_completed and latest_completed.finished_at else None,
            "next_dispatch_at": None,
            "beat_interval_seconds": CAMPAIGN_BEAT_INTERVAL_SECONDS,
            "detail": "Queued for worker pickup. Sending starts when the worker consumes this job.",
        }

    if campaign.status == "active" and settings.BACKGROUND_WORKERS_ENABLED:
        next_dispatch = _next_campaign_beat_at(now)
        return {
            "state": "waiting_for_beat",
            "job_id": None,
            "job_created_at": None,
            "job_started_at": None,
            "last_completed_at": latest_completed.finished_at.isoformat() if latest_completed and latest_completed.finished_at else None,
            "next_dispatch_at": next_dispatch.isoformat(),
            "beat_interval_seconds": CAMPAIGN_BEAT_INTERVAL_SECONDS,
            "detail": "No job is running right now. The next automatic campaign pass will be queued by beat.",
        }

    return {
        "state": "idle",
        "job_id": None,
        "job_created_at": None,
        "job_started_at": None,
        "last_completed_at": latest_completed.finished_at.isoformat() if latest_completed and latest_completed.finished_at else None,
        "next_dispatch_at": None,
        "beat_interval_seconds": CAMPAIGN_BEAT_INTERVAL_SECONDS,
        "detail": "Campaign dispatch runs only after the campaign is active.",
    }


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
        "campaign_type": campaign.campaign_type,
        "channel_type": campaign.channel_type,
        "goal_type": campaign.goal_type,
        "list_strategy": campaign.list_strategy,
        "compliance_mode": campaign.compliance_mode,
        "schedule_window": campaign.schedule_window,
        "send_window_timezone": campaign.send_window_timezone,
        "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
        "lead_count": campaign_lists_summary["lead_count"],
        "sent_count": sent_count,
        "reply_rate": "0%",
        "lists_summary": campaign_lists_summary,
        "execution_summary": _campaign_execution_summary(db, campaign),
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
        daily_limit=req.daily_limit,
        campaign_type=req.campaign_type,
        channel_type=req.channel_type,
        goal_type=req.goal_type,
        list_strategy=req.list_strategy,
        compliance_mode=req.compliance_mode,
        schedule_window=req.schedule_window,
        send_window_timezone=req.send_window_timezone,
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
    campaign.campaign_type = req.campaign_type
    campaign.channel_type = req.channel_type
    campaign.goal_type = req.goal_type
    campaign.list_strategy = req.list_strategy
    campaign.compliance_mode = req.compliance_mode
    campaign.schedule_window = req.schedule_window
    campaign.send_window_timezone = req.send_window_timezone
    db.commit()
    db.refresh(campaign)
    return _campaign_payload(db, campaign)


@router.delete("/{campaign_id}")
def delete_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != "draft":
        raise HTTPException(
            status_code=409,
            detail="Only draft campaigns can be deleted. Pause or archive non-draft campaigns instead.",
        )

    db.query(CampaignLead).filter(CampaignLead.campaign_id == campaign.id).delete(synchronize_session=False)
    db.query(CampaignList).filter(CampaignList.campaign_id == campaign.id).delete(synchronize_session=False)
    for job in db.query(JobLog).filter(JobLog.payload_summary.isnot(None)).all():
        payload_summary = job.payload_summary or {}
        if payload_summary.get("campaign_id") == str(campaign.id):
            db.delete(job)
    db.delete(campaign)
    db.commit()
    return {"status": "deleted", "id": str(campaign.id)}


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

    # Re-sync attached list members into scheduled campaign leads at start time.
    # This keeps campaign execution aligned with the current verification/contact-type/
    # consent state even when a lead became eligible after the list was attached.
    service = LeadListService(db)
    service.sync_campaign_leads(campaign_id)

    scheduled_leads = (
        db.query(CampaignLead)
        .join(Contact)
        .filter(
            CampaignLead.campaign_id == c.id,
            CampaignLead.status == "scheduled",
        )
        .all()
    )
    blocked_counts: dict[str, int] = {}
    eligible_leads = 0
    for lead in scheduled_leads:
        eligibility = evaluate_contact_for_campaign(lead.contact, c)
        if eligibility.eligible:
            eligible_leads += 1
            continue
        reason = eligibility.blocked_reason or "unknown"
        blocked_counts[reason] = blocked_counts.get(reason, 0) + 1
    if eligible_leads == 0:
        raise HTTPException(
            status_code=409,
            detail="Campaign cannot start until it has at least one scheduled, eligible lead after verification, suppression, contact type, and compliance checks.",
        )

    existing_job = _campaign_job_for_status(db, str(c.id), {"queued", "running"})
    if existing_job:
        if c.status != "active":
            c.status = "active"
            db.commit()
        return {
            "status": existing_job.status,
            "campaign": c.name,
            "eligible_leads": eligible_leads,
            "blocked_leads": blocked_counts,
            "job_queued": True,
            "job_id": existing_job.job_id,
        }

    try:
        task = run_campaign_cycle.delay(str(c.id))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Campaign execution could not be queued because background workers are unavailable.",
        ) from exc

    c.status = "active"
    job_id = task.id
    try:
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
    except Exception as exc:
        db.rollback()
        c.status = "draft"
        db.commit()
        raise HTTPException(
            status_code=503,
            detail="Campaign execution could not be recorded after queueing. Try again after checking worker health.",
        ) from exc

    return {
        "status": "queued",
        "campaign": c.name,
        "eligible_leads": eligible_leads,
        "blocked_leads": blocked_counts,
        "job_queued": True,
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
    unsubscribed = sum(1 for c in leads if c.unsubscribe_status in {"unsubscribed", "suppressed"})
    
    return {
        "valid": valid,
        "risky": risky,
        "invalid": invalid,
        "suppressed": suppressed,
        "unsubscribed": unsubscribed,
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
