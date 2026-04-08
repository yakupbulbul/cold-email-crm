from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import settings
from app.core.database import get_db
from app.models.monitoring import JobLog
from app.models.lists import LeadListMember
from app.models.suppression import SuppressionList
from app.services.audience_service import normalize_tags, quality_tier_for_contact
from app.services.verification_service import EmailVerificationService, contact_is_reachable, verification_result_payload
from app.services.import_service import CSVParserService, LeadImportJobService
from app.workers.lead_verification_worker import run_lead_verification_bulk
from app.schemas.import_job import ImportMappingRules
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import io
import csv

from app.models.campaign import Contact

router = APIRouter()


def _serialize_contact(db: Session, contact: Contact) -> dict:
    memberships = db.query(LeadListMember).filter(LeadListMember.lead_id == contact.id).all()
    return {
        "id": str(contact.id),
        "email": contact.email,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "company": contact.company,
        "job_title": contact.job_title,
        "website": contact.website,
        "country": contact.country,
        "industry": contact.industry,
        "persona": contact.persona,
        "contact_type": contact.contact_type,
        "consent_status": contact.consent_status,
        "unsubscribe_status": contact.unsubscribe_status,
        "engagement_score": contact.engagement_score,
        "contact_status": contact.contact_status,
        "email_status": contact.email_status,
        "verification_score": contact.verification_score,
        "verification_integrity": contact.verification_integrity,
        "contact_quality_tier": quality_tier_for_contact(contact),
        "last_verified_at": contact.last_verified_at.isoformat() if contact.last_verified_at else None,
        "last_contacted_at": contact.last_contacted_at.isoformat() if contact.last_contacted_at else None,
        "last_replied_at": contact.last_replied_at.isoformat() if contact.last_replied_at else None,
        "is_disposable": contact.is_disposable,
        "is_role_based": contact.is_role_based,
        "is_suppressed": contact.is_suppressed,
        "verification_reasons": contact.verification_reasons,
        "source": contact.source,
        "source_file_name": contact.source_file_name,
        "tags": normalize_tags(contact.tags),
        "source_import_job_id": str(contact.source_import_job_id) if contact.source_import_job_id else None,
        "list_ids": [str(member.list_id) for member in memberships],
        "list_names": [member.lead_list.name for member in memberships],
        "created_at": contact.created_at.isoformat() if contact.created_at else None,
    }

@router.get("/")
@router.get("")  # Handle both /leads and /leads/ without redirect
def list_leads(
    contact_type: str | None = Query(default=None),
    email_status: str | None = Query(default=None),
    verification_integrity: str | None = Query(default=None),
    consent_status: str | None = Query(default=None),
    unsubscribe_status: str | None = Query(default=None),
    company: str | None = Query(default=None),
    country: str | None = Query(default=None),
    list_id: str | None = Query(default=None),
    min_score: int | None = Query(default=None),
    min_engagement_score: int | None = Query(default=None),
    tag: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Contact)
    if contact_type:
        if contact_type == "mixed":
            query = query.filter(Contact.contact_type.is_(None))
        else:
            query = query.filter(Contact.contact_type == contact_type)
    if email_status:
        query = query.filter(Contact.email_status == email_status)
    if verification_integrity:
        query = query.filter(Contact.verification_integrity == verification_integrity)
    if consent_status:
        query = query.filter(Contact.consent_status == consent_status)
    if unsubscribe_status:
        query = query.filter(Contact.unsubscribe_status == unsubscribe_status)
    if company:
        query = query.filter(Contact.company.ilike(f"%{company}%"))
    if country:
        query = query.filter(Contact.country.ilike(f"%{country}%"))
    if min_score is not None:
        query = query.filter(Contact.verification_score >= min_score)
    if min_engagement_score is not None:
        query = query.filter(Contact.engagement_score >= min_engagement_score)
    if list_id:
        query = query.join(LeadListMember, LeadListMember.lead_id == Contact.id).filter(LeadListMember.list_id == list_id)
    contacts = query.all()
    if tag:
        contacts = [contact for contact in contacts if tag in normalize_tags(contact.tags)]
    return [_serialize_contact(db, contact) for contact in contacts]

@router.post("/import/csv")
async def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Invalid file type. Must be CSV.")
    
    contents = await file.read()
    parser = CSVParserService(db)
    job = parser.create_import_job(contents, file.filename)
    
    return {"job_id": job.id, "status": job.status, "total_rows_parsed": job.total_rows}

@router.post("/import/{job_id}/map")
def map_and_validate_import(job_id: str, mappings: ImportMappingRules, db: Session = Depends(get_db)):
    importer = LeadImportJobService(db)
    importer.validate_and_map_job(job_id, mappings)
    
    # Fetch updated job
    from app.models.import_job import LeadImportJob
    job = db.query(LeadImportJob).filter(LeadImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return {
        "job_id": job.id,
        "status": job.status,
        "valid_rows": job.valid_rows,
        "invalid_rows": job.invalid_rows,
        "duplicate_rows": job.duplicate_rows
    }

@router.post("/import/{job_id}/confirm")
def confirm_import(job_id: str, db: Session = Depends(get_db)):
    importer = LeadImportJobService(db)
    importer.confirm_and_import(job_id)
    
    from app.models.import_job import LeadImportJob
    job = db.query(LeadImportJob).filter(LeadImportJob.id == job_id).first()
    return {"job_id": job.id, "status": job.status, "imported_rows": job.imported_rows}

@router.get("/import/{job_id}")
def get_import_job(job_id: str, db: Session = Depends(get_db)):
    from app.models.import_job import LeadImportJob, LeadImportRow
    job = db.query(LeadImportJob).filter(LeadImportJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    rows = db.query(LeadImportRow).filter(LeadImportRow.job_id == job_id).limit(100).all()
    
    return {
        "job": {
            "id": job.id,
            "file_name": job.file_name,
            "status": job.status,
            "total": job.total_rows,
            "valid": job.valid_rows,
            "invalid": job.invalid_rows
        },
        "preview_rows": rows
    }

class VerifyRequest(BaseModel):
    lead_id: UUID


class VerifyBulkRequest(BaseModel):
    lead_ids: list[UUID]


class LeadBulkTagsRequest(BaseModel):
    lead_ids: list[UUID]
    tags: list[str]


class LeadBulkSuppressRequest(BaseModel):
    lead_ids: list[UUID]
    reason: str = "manual_bulk_action"


class LeadUpdateRequest(BaseModel):
    contact_type: Literal["b2b", "b2c", "mixed"] | None


class LeadBulkContactTypeRequest(BaseModel):
    lead_ids: list[UUID]
    contact_type: Literal["b2b", "b2c", "mixed"] | None


@router.patch("/{lead_id}")
def update_lead(lead_id: UUID, req: LeadUpdateRequest, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == lead_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Lead not found")

    contact.contact_type = None if req.contact_type in {None, "mixed"} else req.contact_type
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return _serialize_contact(db, contact)


@router.patch("/bulk/contact-type")
def update_lead_contact_type_bulk(req: LeadBulkContactTypeRequest, db: Session = Depends(get_db)):
    contacts = db.query(Contact).filter(Contact.id.in_(req.lead_ids)).all()
    if len(contacts) != len(set(req.lead_ids)):
        raise HTTPException(status_code=404, detail="One or more leads were not found")

    normalized_contact_type = None if req.contact_type in {None, "mixed"} else req.contact_type
    for contact in contacts:
        contact.contact_type = normalized_contact_type
        db.add(contact)
    db.commit()

    return {
        "status": "updated",
        "lead_count": len(contacts),
        "contact_type": normalized_contact_type,
    }

@router.post("/verify")
def verify_email(req: VerifyRequest, db: Session = Depends(get_db)):
    service = EmailVerificationService(db)
    try:
        result = service.verify_lead(str(req.lead_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return verification_result_payload(result)


@router.post("/verify/bulk")
def verify_leads_bulk(req: VerifyBulkRequest, db: Session = Depends(get_db)):
    lead_ids = [str(lead_id) for lead_id in req.lead_ids]
    if not lead_ids:
        raise HTTPException(status_code=400, detail="At least one lead_id is required")

    job = JobLog(
        job_id=f"lead-verify-{datetime.utcnow().timestamp()}",
        job_type="lead_verification_bulk",
        status="queued",
        payload_summary={"lead_ids": lead_ids, "requested_count": len(lead_ids), "processed_count": 0, "results": []},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    if settings.BACKGROUND_WORKERS_ENABLED:
        task = run_lead_verification_bulk.delay(lead_ids)
        job.job_id = task.id
        db.commit()
        db.refresh(job)
    else:
        service = EmailVerificationService(db)
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        results = [verification_result_payload(result) for result in service.verify_leads(lead_ids)]
        job.status = "completed"
        job.finished_at = datetime.utcnow()
        job.payload_summary = {
            "lead_ids": lead_ids,
            "requested_count": len(lead_ids),
            "processed_count": len(results),
            "results": results,
            "worker_mode": "lean",
        }
        flag_modified(job, "payload_summary")
        db.add(job)
        db.commit()
        db.refresh(job)

    return {
        "job_id": job.job_id,
        "status": job.status,
        "requested_count": len(lead_ids),
        "worker_mode": "full" if settings.BACKGROUND_WORKERS_ENABLED else "lean",
    }


@router.get("/verify/{job_id}")
def get_verify_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(JobLog).filter(JobLog.job_id == job_id, JobLog.job_type == "lead_verification_bulk").first()
    if not job:
        raise HTTPException(status_code=404, detail="Verification job not found")

    payload_summary = job.payload_summary or {}
    return {
        "job_id": job.job_id,
        "status": job.status,
        "requested_count": payload_summary.get("requested_count", 0),
        "processed_count": payload_summary.get("processed_count", 0),
        "results": payload_summary.get("results", []),
        "error": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }


@router.patch("/bulk/tags")
def assign_tags_bulk(req: LeadBulkTagsRequest, db: Session = Depends(get_db)):
    contacts = db.query(Contact).filter(Contact.id.in_(req.lead_ids)).all()
    if len(contacts) != len(set(req.lead_ids)):
        raise HTTPException(status_code=404, detail="One or more leads were not found")
    normalized_tags = sorted(set(normalize_tags(req.tags)))
    for contact in contacts:
        existing = set(normalize_tags(contact.tags))
        contact.tags = sorted(existing.union(normalized_tags))
        db.add(contact)
    db.commit()
    return {"status": "updated", "lead_count": len(contacts), "tags": normalized_tags}


@router.post("/bulk/suppress")
def suppress_leads_bulk(req: LeadBulkSuppressRequest, db: Session = Depends(get_db)):
    contacts = db.query(Contact).filter(Contact.id.in_(req.lead_ids)).all()
    if len(contacts) != len(set(req.lead_ids)):
        raise HTTPException(status_code=404, detail="One or more leads were not found")
    suppressed_count = 0
    for contact in contacts:
        email = contact.email.strip().lower()
        existing = db.query(SuppressionList).filter(SuppressionList.email == email).first()
        if not existing:
            db.add(SuppressionList(email=email, reason=req.reason, source="bulk_contact_action"))
        contact.is_suppressed = True
        contact.unsubscribe_status = "suppressed"
        db.add(contact)
        suppressed_count += 1
    db.commit()
    return {"status": "suppressed", "lead_count": suppressed_count}

def generate_csv_response(contacts, filename):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Email", "First Name", "Last Name", "Company", "Contact Type", "Consent Status",
        "Unsubscribe Status", "Verification Score", "Engagement Score", "Tags", "Suppressed"
    ])
    for c in contacts:
        writer.writerow([
            c.email, c.first_name, c.last_name, c.company, c.contact_type, c.consent_status,
            c.unsubscribe_status, c.verification_score, c.engagement_score, ",".join(normalize_tags(c.tags)), c.is_suppressed
        ])
    output.seek(0)
    return StreamingResponse(io.BytesIO(output.getvalue().encode('utf-8')), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={filename}"})

@router.get("/export")
def export_all_contacts(db: Session = Depends(get_db)):
    from app.models.campaign import Contact
    contacts = db.query(Contact).all()
    return generate_csv_response(contacts, "all_contacts.csv")

@router.get("/export/invalid")
def export_invalid_contacts(db: Session = Depends(get_db)):
    from app.models.campaign import Contact
    contacts = [contact for contact in db.query(Contact).all() if not contact_is_reachable(contact)]
    return generate_csv_response(contacts, "invalid_contacts.csv")

@router.get("/export/suppressed")
def export_suppressed_contacts(db: Session = Depends(get_db)):
    from app.models.campaign import Contact
    contacts = db.query(Contact).filter(Contact.is_suppressed == True).all()
    return generate_csv_response(contacts, "suppressed_contacts.csv")
