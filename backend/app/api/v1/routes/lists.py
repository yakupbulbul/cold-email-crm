from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.campaign import Contact
from app.models.lists import LeadList, LeadListMember
from app.services.audience_service import normalize_tags, quality_tier_for_contact
from app.schemas.lists import LeadListCreate, LeadListLeadBulkPayload, LeadListLeadPayload, LeadListUpdate
from app.services.list_service import LeadListService

router = APIRouter()


def _get_list_or_404(db: Session, list_id: str) -> LeadList:
    try:
        return LeadListService(db).get_list_or_404(list_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("")
@router.post("/")
def create_list(req: LeadListCreate, db: Session = Depends(get_db)):
    service = LeadListService(db)
    try:
        normalized_name = service.validate_list_name(req.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if req.type != "static":
        raise HTTPException(status_code=400, detail="Only static lists are supported right now.")
    lead_list = LeadList(
        name=normalized_name,
        description=req.description,
        type="static",
        filter_definition=req.filter_definition,
    )
    db.add(lead_list)
    db.commit()
    db.refresh(lead_list)
    return service.summarize_list(lead_list)


@router.get("")
@router.get("/")
def list_lists(db: Session = Depends(get_db)):
    service = LeadListService(db)
    return [service.summarize_list(item) for item in db.query(LeadList).order_by(LeadList.created_at.desc()).all()]


@router.get("/{list_id}")
def get_list(list_id: str, db: Session = Depends(get_db)):
    service = LeadListService(db)
    return service.summarize_list(_get_list_or_404(db, list_id))


@router.patch("/{list_id}")
def update_list(list_id: str, req: LeadListUpdate, db: Session = Depends(get_db)):
    service = LeadListService(db)
    lead_list = _get_list_or_404(db, list_id)
    if req.name is not None:
        try:
            lead_list.name = service.validate_list_name(req.name, current_list_id=list_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if req.description is not None:
        lead_list.description = req.description
    if req.type is not None and req.type != lead_list.type:
        raise HTTPException(status_code=400, detail="Changing list type is not supported.")
    if req.filter_definition is not None:
        lead_list.filter_definition = req.filter_definition
    db.commit()
    db.refresh(lead_list)
    return service.summarize_list(lead_list)


@router.delete("/{list_id}")
def delete_list(list_id: str, db: Session = Depends(get_db)):
    lead_list = _get_list_or_404(db, list_id)
    affected_campaign_ids = [str(item.campaign_id) for item in lead_list.campaigns]
    db.delete(lead_list)
    db.commit()
    service = LeadListService(db)
    for campaign_id in affected_campaign_ids:
        service.sync_campaign_leads(campaign_id)
    return {"status": "deleted", "id": list_id}


@router.get("/{list_id}/leads")
def get_list_leads(list_id: str, db: Session = Depends(get_db)):
    lead_list = _get_list_or_404(db, list_id)
    service = LeadListService(db)
    contacts = [member.lead for member in lead_list.members]
    return {
        "list": service.summarize_list(lead_list),
        "leads": [
            {
                "id": str(contact.id),
                "email": contact.email,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "company": contact.company,
                "contact_type": contact.contact_type,
                "consent_status": contact.consent_status,
                "unsubscribe_status": contact.unsubscribe_status,
                "engagement_score": contact.engagement_score,
                "email_status": contact.email_status,
                "verification_score": contact.verification_score,
                "verification_integrity": contact.verification_integrity,
                "contact_quality_tier": quality_tier_for_contact(contact),
                "is_suppressed": contact.is_suppressed,
                "tags": normalize_tags(contact.tags),
                "created_at": contact.created_at.isoformat() if contact.created_at else None,
            }
            for contact in contacts
        ],
    }


@router.post("/{list_id}/leads")
def add_lead_to_list(list_id: str, req: LeadListLeadPayload, db: Session = Depends(get_db)):
    lead_list = _get_list_or_404(db, list_id)
    contact = db.query(Contact).filter(Contact.id == req.lead_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Lead not found")
    existing = db.query(LeadListMember).filter(LeadListMember.list_id == lead_list.id, LeadListMember.lead_id == contact.id).first()
    if not existing:
        db.add(LeadListMember(list_id=lead_list.id, lead_id=contact.id))
        db.commit()
    service = LeadListService(db)
    for attached in lead_list.campaigns:
        service.sync_campaign_leads(str(attached.campaign_id))
    return service.summarize_list(_get_list_or_404(db, list_id))


@router.post("/{list_id}/leads/bulk")
def add_leads_to_list_bulk(list_id: str, req: LeadListLeadBulkPayload, db: Session = Depends(get_db)):
    lead_list = _get_list_or_404(db, list_id)
    lead_ids = [str(lead_id) for lead_id in req.lead_ids]
    contacts = db.query(Contact).filter(Contact.id.in_(req.lead_ids)).all()
    if len(contacts) != len(set(lead_ids)):
        raise HTTPException(status_code=404, detail="One or more leads were not found")
    existing_ids = {
        str(member.lead_id)
        for member in db.query(LeadListMember).filter(LeadListMember.list_id == lead_list.id, LeadListMember.lead_id.in_(req.lead_ids)).all()
    }
    for contact in contacts:
        if str(contact.id) in existing_ids:
            continue
        db.add(LeadListMember(list_id=lead_list.id, lead_id=contact.id))
    db.commit()
    service = LeadListService(db)
    for attached in lead_list.campaigns:
        service.sync_campaign_leads(str(attached.campaign_id))
    return service.summarize_list(_get_list_or_404(db, list_id))


@router.delete("/{list_id}/leads/{lead_id}")
def remove_lead_from_list(list_id: str, lead_id: str, db: Session = Depends(get_db)):
    lead_list = _get_list_or_404(db, list_id)
    membership = db.query(LeadListMember).filter(LeadListMember.list_id == lead_list.id, LeadListMember.lead_id == lead_id).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Lead is not a member of this list")
    db.delete(membership)
    db.commit()
    service = LeadListService(db)
    for attached in lead_list.campaigns:
        service.sync_campaign_leads(str(attached.campaign_id))
    return {"status": "removed", "list_id": list_id, "lead_id": lead_id}
