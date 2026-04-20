from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.database import get_db
from app.models.campaign import Campaign, CampaignLead, CampaignSequenceStep, Contact, EmailTemplate, SendLog
from app.models.lists import CampaignList
from app.models.monitoring import JobLog
from app.schemas.campaign import (
    CampaignCreate,
    CampaignResponse,
    CampaignSequenceStepPayload,
    EmailTemplateCreate,
    EmailTemplateUpdate,
    CampaignUpdate,
)
from app.schemas.lists import CampaignListAttachPayload
from app.services.audience_service import evaluate_contact_for_campaign
from app.services.list_service import LeadListService
from app.workers.campaign_worker import run_campaign_cycle

router = APIRouter()
CAMPAIGN_BEAT_INTERVAL_SECONDS = 300


def _campaign_job_for_status(db: Session, campaign_id: str, statuses: set[str]) -> JobLog | None:
    stale_after = datetime.utcnow() - timedelta(seconds=CAMPAIGN_BEAT_INTERVAL_SECONDS * 2)
    for job in db.query(JobLog).filter(JobLog.job_type == "campaign_cycle").order_by(JobLog.created_at.desc()).all():
        payload_summary = job.payload_summary or {}
        if payload_summary.get("campaign_id") != campaign_id or job.status not in statuses:
            continue
        if job.status == "queued" and job.created_at and job.created_at < stale_after:
            continue
        if job.status == "running":
            last_seen = job.started_at or job.created_at
            if last_seen and last_seen < stale_after:
                continue
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


def _campaign_job_history(jobs: list[JobLog], limit: int = 8) -> list[dict]:
    return [
        {
            "job_id": job.job_id,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "error_message": job.error_message,
            "retry_count": job.retry_count,
            "payload_summary": job.payload_summary or {},
        }
        for job in jobs[:limit]
    ]


def _next_campaign_beat_at(now: datetime) -> datetime:
    interval_minutes = CAMPAIGN_BEAT_INTERVAL_SECONDS // 60
    next_boundary_minute = ((now.minute // interval_minutes) + 1) * interval_minutes
    if next_boundary_minute >= 60:
        return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    return now.replace(minute=next_boundary_minute, second=0, microsecond=0)


def _scheduled_lead_snapshot(db: Session, campaign: Campaign) -> dict:
    scheduled_leads = (
        db.query(CampaignLead)
        .join(Contact)
        .filter(
            CampaignLead.campaign_id == campaign.id,
            CampaignLead.status == "scheduled",
        )
        .order_by(CampaignLead.scheduled_at.asc().nullsfirst(), CampaignLead.created_at.asc())
        .all()
    )
    blocked_counts: dict[str, int] = {}
    eligible_count = 0
    next_eligible = None
    for lead in scheduled_leads:
        eligibility = evaluate_contact_for_campaign(lead.contact, campaign)
        if eligibility.eligible:
            eligible_count += 1
            if next_eligible is None:
                next_eligible = {
                    "campaign_lead_id": str(lead.id),
                    "contact_id": str(lead.contact_id),
                    "email": lead.contact.email,
                    "scheduled_at": lead.scheduled_at.isoformat() if lead.scheduled_at else None,
                    "warning_reason": eligibility.warning_reason,
                }
            continue
        reason = eligibility.blocked_reason or "unknown"
        blocked_counts[reason] = blocked_counts.get(reason, 0) + 1
    return {
        "scheduled_count": len(scheduled_leads),
        "eligible_count": eligible_count,
        "blocked_counts": blocked_counts,
        "next_eligible_lead": next_eligible,
    }


def _campaign_dry_run(db: Session, campaign: Campaign) -> dict:
    LeadListService(db).sync_campaign_leads(str(campaign.id))
    lead_snapshot = _scheduled_lead_snapshot(db, campaign)

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sent_today = db.query(SendLog).filter(
        SendLog.campaign_id == campaign.id,
        SendLog.created_at >= today,
        SendLog.delivery_status == "success",
    ).count()
    remaining_today = max((campaign.daily_limit or 0) - sent_today, 0)

    blockers: list[dict] = []
    warnings: list[dict] = []

    if campaign.status == "archived":
        blockers.append({"code": "archived", "message": "Archived campaigns cannot send until restored."})
    if not settings.BACKGROUND_WORKERS_ENABLED:
        blockers.append({"code": "workers_disabled", "message": "Background workers are disabled in the current runtime mode."})
    if not campaign.mailbox:
        blockers.append({"code": "missing_mailbox", "message": "Campaign has no selected sending mailbox."})
    if lead_snapshot["eligible_count"] == 0:
        blockers.append({
            "code": "no_eligible_leads",
            "message": "No scheduled leads are eligible after verification, suppression, contact type, and compliance checks.",
        })
    if remaining_today <= 0:
        blockers.append({"code": "daily_limit_reached", "message": "Campaign daily send limit is already reached for today."})

    deliverability = None
    try:
        from app.services.deliverability_service import DeliverabilityService
        deliverability = DeliverabilityService(db).campaign_readiness(str(campaign.id))
        if deliverability.get("status") == "blocked":
            primary = (deliverability.get("blockers") or [{}])[0]
            blockers.append({
                "code": "deliverability_blocked",
                "message": primary.get("message") or "Campaign deliverability readiness is blocked.",
            })
        elif deliverability.get("status") in {"warning", "degraded", "unknown"}:
            warnings.append({
                "code": "deliverability_warning",
                "message": f"Deliverability posture is {deliverability.get('status')}. Review warnings before scaling.",
            })
    except Exception as exc:
        warnings.append({"code": "deliverability_unavailable", "message": f"Deliverability readiness could not be evaluated: {exc}"})

    existing_job = _campaign_job_for_status(db, str(campaign.id), {"queued", "running"})
    if existing_job:
        blockers.append({
            "code": "job_already_active",
            "message": f"A campaign worker job is already {existing_job.status}.",
        })

    schedule_allowed_now = True
    next_send_at = datetime.utcnow() if schedule_allowed_now and not blockers else _next_campaign_beat_at(datetime.utcnow())
    sender_identity = None
    if campaign.mailbox:
        display_name = (campaign.mailbox.display_name or "").strip()
        sender_identity = f"{display_name} <{campaign.mailbox.email}>" if display_name else campaign.mailbox.email

    return {
        "campaign_id": str(campaign.id),
        "campaign": campaign.name,
        "campaign_status": campaign.status,
        "mailbox_id": str(campaign.mailbox_id) if campaign.mailbox_id else None,
        "mailbox_email": campaign.mailbox.email if campaign.mailbox else None,
        "sender_identity": sender_identity,
        "eligible_leads": lead_snapshot["eligible_count"],
        "scheduled_leads": lead_snapshot["scheduled_count"],
        "blocked_leads": lead_snapshot["blocked_counts"],
        "next_eligible_lead": lead_snapshot["next_eligible_lead"],
        "sent_today": sent_today,
        "daily_limit": campaign.daily_limit,
        "remaining_today": remaining_today,
        "schedule_allows_now": schedule_allowed_now,
        "schedule_detail": "No campaign send window is configured, so the worker may send on its next pass.",
        "next_send_at": next_send_at.isoformat() if next_send_at else None,
        "deliverability_status": deliverability.get("status") if deliverability else "unknown",
        "deliverability": deliverability,
        "would_queue": not blockers,
        "blockers": blockers,
        "warnings": warnings,
    }


def _campaign_execution_summary(db: Session, campaign: Campaign) -> dict:
    now = datetime.utcnow()
    jobs = _campaign_jobs_for_campaign(db, str(campaign.id))
    latest_job = jobs[0] if jobs else None
    stale_after = now - timedelta(seconds=CAMPAIGN_BEAT_INTERVAL_SECONDS * 2)
    latest_running = next(
        (
            job for job in jobs
            if job.status == "running"
            and (job.started_at or job.created_at)
            and (job.started_at or job.created_at) >= stale_after
        ),
        None,
    )
    latest_completed = next((job for job in jobs if job.status == "completed"), None)
    latest_failed = next((job for job in jobs if job.status == "failed"), None)
    latest_send_log = (
        db.query(SendLog)
        .filter(SendLog.campaign_id == campaign.id)
        .order_by(SendLog.created_at.desc())
        .first()
    )

    delivery_summary = {
        "last_delivery_attempt_at": latest_send_log.created_at.isoformat() if latest_send_log and latest_send_log.created_at else None,
        "last_delivery_status": latest_send_log.delivery_status if latest_send_log else None,
        "last_delivery_target_email": latest_send_log.target_email if latest_send_log else None,
        "last_delivery_error": latest_send_log.smtp_response if latest_send_log and latest_send_log.delivery_status == "failed" else None,
    }
    lead_snapshot = _scheduled_lead_snapshot(db, campaign)
    job_history = _campaign_job_history(jobs)
    base_summary = {
        "last_job_queued_at": next((job.created_at.isoformat() for job in jobs if job.status == "queued" and job.created_at), None),
        "last_job_started_at": next((job.started_at.isoformat() for job in jobs if job.started_at), None),
        "last_job_completed_at": latest_completed.finished_at.isoformat() if latest_completed and latest_completed.finished_at else None,
        "last_job_failed_at": latest_failed.finished_at.isoformat() if latest_failed and latest_failed.finished_at else None,
        "last_job_error": latest_failed.error_message if latest_failed else None,
        "job_history": job_history,
        "eligible_leads": lead_snapshot["eligible_count"],
        "scheduled_leads": lead_snapshot["scheduled_count"],
        "blocked_leads": lead_snapshot["blocked_counts"],
        "next_eligible_lead": lead_snapshot["next_eligible_lead"],
    }

    if campaign.status == "archived":
        return {
            "state": "archived",
            "job_id": None,
            "job_created_at": None,
            "job_started_at": None,
            "last_completed_at": latest_completed.finished_at.isoformat() if latest_completed and latest_completed.finished_at else None,
            "next_dispatch_at": None,
            "beat_interval_seconds": CAMPAIGN_BEAT_INTERVAL_SECONDS,
            "detail": "Archived campaigns are excluded from automatic execution until they are restored manually.",
            "current_blocker": {"code": "archived", "message": "Archived campaigns are excluded from execution."},
            "next_send_decision": "Restore the campaign before it can dispatch.",
            **base_summary,
            **delivery_summary,
        }

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
            "current_blocker": None,
            "next_send_decision": "Worker is running now.",
            **base_summary,
            **delivery_summary,
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
            "current_blocker": None,
            "next_send_decision": "Worker pickup is pending.",
            **base_summary,
            **delivery_summary,
        }

    if campaign.status == "active" and settings.BACKGROUND_WORKERS_ENABLED:
        next_dispatch = _next_campaign_beat_at(now)
        current_blocker = None
        next_send_decision = f"Next automatic campaign pass is scheduled for {next_dispatch.isoformat()}."
        if lead_snapshot["eligible_count"] == 0:
            current_blocker = {"code": "no_eligible_leads", "message": "No scheduled eligible leads are available for the next pass."}
            next_send_decision = "Add or verify eligible leads before the next pass can send."
        detail = "No job is running right now. The next automatic campaign pass will be queued by beat."
        if latest_send_log and latest_send_log.delivery_status == "failed":
            detail = "No job is running right now. The last delivery attempt failed, and the next automatic campaign pass will be queued by beat."
        return {
            "state": "waiting_for_beat",
            "job_id": None,
            "job_created_at": None,
            "job_started_at": None,
            "last_completed_at": latest_completed.finished_at.isoformat() if latest_completed and latest_completed.finished_at else None,
            "next_dispatch_at": next_dispatch.isoformat(),
            "beat_interval_seconds": CAMPAIGN_BEAT_INTERVAL_SECONDS,
            "detail": detail,
            "current_blocker": current_blocker,
            "next_send_decision": next_send_decision,
            **base_summary,
            **delivery_summary,
        }

    current_blocker = None
    next_send_decision = "Campaign dispatch runs only after the campaign is active."
    if not settings.BACKGROUND_WORKERS_ENABLED:
        current_blocker = {"code": "workers_disabled", "message": "Background workers are disabled in the current runtime mode."}
        next_send_decision = "Start the app with workers enabled before campaigns can dispatch."
    elif lead_snapshot["eligible_count"] == 0:
        current_blocker = {"code": "no_eligible_leads", "message": "No scheduled eligible leads are available."}
        next_send_decision = "Attach or verify leads before starting this campaign."

    return {
        "state": "idle",
        "job_id": None,
        "job_created_at": None,
        "job_started_at": None,
        "last_completed_at": latest_completed.finished_at.isoformat() if latest_completed and latest_completed.finished_at else None,
        "next_dispatch_at": None,
        "beat_interval_seconds": CAMPAIGN_BEAT_INTERVAL_SECONDS,
        "detail": "Campaign dispatch runs only after the campaign is active.",
        "current_blocker": current_blocker,
        "next_send_decision": next_send_decision,
        **base_summary,
        **delivery_summary,
    }


def _campaign_execution_detail(db: Session, campaign: Campaign) -> dict:
    summary = _campaign_execution_summary(db, campaign)
    dry_run = _campaign_dry_run(db, campaign)
    return {
        "campaign_id": str(campaign.id),
        "campaign": campaign.name,
        "summary": summary,
        "dry_run": dry_run,
        "job_history": summary.get("job_history", []),
        "next_eligible_lead": summary.get("next_eligible_lead"),
        "current_blocker": summary.get("current_blocker"),
        "next_send_decision": summary.get("next_send_decision"),
    }


def _queue_campaign_pass(db: Session, campaign: Campaign, *, action: str) -> dict:
    dry_run = _campaign_dry_run(db, campaign)
    existing_job = _campaign_job_for_status(db, str(campaign.id), {"queued", "running"})
    blocking_without_active_job = [blocker for blocker in dry_run["blockers"] if blocker.get("code") != "job_already_active"]
    if blocking_without_active_job:
        raise HTTPException(status_code=409, detail=blocking_without_active_job[0]["message"])

    if existing_job:
        return {
            "status": existing_job.status,
            "campaign": campaign.name,
            "eligible_leads": dry_run["eligible_leads"],
            "blocked_leads": dry_run["blocked_leads"],
            "job_queued": True,
            "job_id": existing_job.job_id,
            "execution": _campaign_execution_detail(db, campaign),
        }

    try:
        task = run_campaign_cycle.delay(str(campaign.id))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Campaign execution could not be queued because background workers are unavailable.",
        ) from exc

    campaign.status = "active"
    db.add(
        JobLog(
            job_id=task.id,
            job_type="campaign_cycle",
            status="queued",
            payload_summary={
                "campaign_id": str(campaign.id),
                "campaign_name": campaign.name,
                "eligible_leads": dry_run["eligible_leads"],
                "action": action,
            },
        )
    )
    db.commit()
    db.refresh(campaign)
    return {
        "status": "queued",
        "campaign": campaign.name,
        "eligible_leads": dry_run["eligible_leads"],
        "blocked_leads": dry_run["blocked_leads"],
        "job_queued": True,
        "job_id": task.id,
        "execution": _campaign_execution_detail(db, campaign),
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
        "sequence_steps_count": len(campaign.sequence_steps or []),
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
    db.add(
        CampaignSequenceStep(
            campaign_id=c.id,
            step_number=1,
            delay_days=0,
            subject=c.template_subject,
            body=c.template_body,
            stop_on_reply=True,
        )
    )
    db.commit()
    db.refresh(c)
    return _campaign_payload(db, c)


def _template_payload(template: EmailTemplate) -> dict:
    return {
        "id": str(template.id),
        "name": template.name,
        "subject": template.subject,
        "body": template.body,
        "created_at": template.created_at.isoformat() if template.created_at else None,
        "updated_at": template.updated_at.isoformat() if template.updated_at else None,
    }


def _sequence_step_payload(step: CampaignSequenceStep) -> dict:
    return {
        "id": str(step.id),
        "campaign_id": str(step.campaign_id),
        "step_number": step.step_number,
        "delay_days": step.delay_days,
        "subject": step.subject,
        "body": step.body,
        "stop_on_reply": step.stop_on_reply,
        "created_at": step.created_at.isoformat() if step.created_at else None,
        "updated_at": step.updated_at.isoformat() if step.updated_at else None,
    }


@router.get("/templates")
def list_email_templates(db: Session = Depends(get_db)):
    templates = db.query(EmailTemplate).order_by(EmailTemplate.updated_at.desc().nullslast(), EmailTemplate.created_at.desc()).all()
    return [_template_payload(template) for template in templates]


@router.post("/templates")
def create_email_template(req: EmailTemplateCreate, db: Session = Depends(get_db)):
    if not req.name.strip() or not req.subject.strip() or not req.body.strip():
        raise HTTPException(status_code=422, detail="Template name, subject, and body are required.")
    template = EmailTemplate(name=req.name.strip(), subject=req.subject.strip(), body=req.body.strip())
    db.add(template)
    db.commit()
    db.refresh(template)
    return _template_payload(template)


@router.put("/templates/{template_id}")
def update_email_template(template_id: str, req: EmailTemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if not req.name.strip() or not req.subject.strip() or not req.body.strip():
        raise HTTPException(status_code=422, detail="Template name, subject, and body are required.")
    template.name = req.name.strip()
    template.subject = req.subject.strip()
    template.body = req.body.strip()
    db.add(template)
    db.commit()
    db.refresh(template)
    return _template_payload(template)


@router.delete("/templates/{template_id}")
def delete_email_template(template_id: str, db: Session = Depends(get_db)):
    template = db.query(EmailTemplate).filter(EmailTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    db.delete(template)
    db.commit()
    return {"status": "deleted", "id": template_id}


@router.get("/{campaign_id}/sequence")
def get_campaign_sequence(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    steps = db.query(CampaignSequenceStep).filter(CampaignSequenceStep.campaign_id == campaign.id).order_by(CampaignSequenceStep.step_number.asc()).all()
    if not steps:
        fallback = CampaignSequenceStep(
            campaign_id=campaign.id,
            step_number=1,
            delay_days=0,
            subject=campaign.template_subject,
            body=campaign.template_body,
            stop_on_reply=True,
        )
        return [_sequence_step_payload(fallback)]
    return [_sequence_step_payload(step) for step in steps]


@router.put("/{campaign_id}/sequence")
def replace_campaign_sequence(campaign_id: str, req: list[CampaignSequenceStepPayload], db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if not req:
        raise HTTPException(status_code=422, detail="At least one sequence step is required.")

    ordered = sorted(req, key=lambda step: step.step_number)
    seen: set[int] = set()
    for index, step in enumerate(ordered):
        if step.step_number < 1:
            raise HTTPException(status_code=422, detail="Sequence step numbers must start at 1.")
        if step.step_number in seen:
            raise HTTPException(status_code=422, detail="Sequence step numbers must be unique.")
        if index == 0 and step.step_number != 1:
            raise HTTPException(status_code=422, detail="The first sequence step must be step 1.")
        if step.delay_days < 0:
            raise HTTPException(status_code=422, detail="Delay days cannot be negative.")
        if not step.subject.strip() or not step.body.strip():
            raise HTTPException(status_code=422, detail="Every sequence step needs a subject and body.")
        seen.add(step.step_number)

    db.query(CampaignSequenceStep).filter(CampaignSequenceStep.campaign_id == campaign.id).delete(synchronize_session=False)
    for step in ordered:
        db.add(
            CampaignSequenceStep(
                campaign_id=campaign.id,
                step_number=step.step_number,
                delay_days=0 if step.step_number == 1 else step.delay_days,
                subject=step.subject.strip(),
                body=step.body.strip(),
                stop_on_reply=step.stop_on_reply,
            )
        )
    campaign.template_subject = ordered[0].subject.strip()
    campaign.template_body = ordered[0].body.strip()
    db.add(campaign)
    db.commit()
    steps = db.query(CampaignSequenceStep).filter(CampaignSequenceStep.campaign_id == campaign.id).order_by(CampaignSequenceStep.step_number.asc()).all()
    return [_sequence_step_payload(step) for step in steps]


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
    steps = db.query(CampaignSequenceStep).filter(CampaignSequenceStep.campaign_id == campaign.id).order_by(CampaignSequenceStep.step_number.asc()).all()
    if len(steps) <= 1:
        if steps:
            steps[0].subject = req.template_subject
            steps[0].body = req.template_body
            steps[0].delay_days = 0
            db.add(steps[0])
        else:
            db.add(
                CampaignSequenceStep(
                    campaign_id=campaign.id,
                    step_number=1,
                    delay_days=0,
                    subject=req.template_subject,
                    body=req.template_body,
                    stop_on_reply=True,
                )
            )
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


@router.post("/{campaign_id}/archive")
def archive_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == "archived":
        return {"status": "archived", "id": str(campaign.id), "campaign": campaign.name}

    campaign.status = "archived"
    db.commit()
    return {"status": "archived", "id": str(campaign.id), "campaign": campaign.name}


@router.post("/{campaign_id}/unarchive")
def unarchive_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != "archived":
        raise HTTPException(
            status_code=409,
            detail="Only archived campaigns can be restored.",
        )

    campaign.status = "paused"
    db.commit()
    return {"status": "paused", "id": str(campaign.id), "campaign": campaign.name}


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
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if c.status == "archived":
        raise HTTPException(
            status_code=409,
            detail="Archived campaigns cannot be started. Restore or duplicate the campaign before sending again.",
        )

    return _queue_campaign_pass(db, c, action="start")


@router.get("/{campaign_id}/execution")
def campaign_execution(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_execution_detail(db, campaign)


@router.post("/{campaign_id}/retry")
def retry_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == "archived":
        raise HTTPException(status_code=409, detail="Archived campaigns cannot be retried. Restore the campaign first.")
    return _queue_campaign_pass(db, campaign, action="manual_retry")


@router.post("/{campaign_id}/dry-run")
def dry_run_campaign(campaign_id: str, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign_dry_run(db, campaign)
    
@router.post("/{campaign_id}/pause")
def pause_campaign(campaign_id: str, db: Session = Depends(get_db)):
    c = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if c.status == "archived":
        raise HTTPException(status_code=409, detail="Archived campaigns cannot be paused.")
        
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
