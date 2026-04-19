from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.deliverability_service import DeliverabilityService

router = APIRouter()


@router.get("/overview")
def deliverability_overview(db: Session = Depends(get_db)):
    return DeliverabilityService(db).overview()


@router.get("/domains")
def deliverability_domains(db: Session = Depends(get_db)):
    return DeliverabilityService(db).domains()


@router.get("/domains/{domain_id}")
def deliverability_domain(domain_id: str, db: Session = Depends(get_db)):
    result = DeliverabilityService(db).domain_readiness(domain_id)
    if result.get("code") == "domain_not_found" or any(blocker.get("code") == "domain_not_found" for blocker in result.get("blockers", [])):
        raise HTTPException(status_code=404, detail="Domain not found")
    return result


@router.get("/mailboxes")
def deliverability_mailboxes(db: Session = Depends(get_db)):
    return DeliverabilityService(db).mailboxes()


@router.get("/mailboxes/{mailbox_id}")
def deliverability_mailbox(mailbox_id: str, db: Session = Depends(get_db)):
    result = DeliverabilityService(db).mailbox_readiness(mailbox_id)
    if any(blocker.get("code") == "mailbox_not_found" for blocker in result.get("blockers", [])):
        raise HTTPException(status_code=404, detail="Mailbox not found")
    return result


@router.get("/campaigns/{campaign_id}")
def deliverability_campaign(campaign_id: str, db: Session = Depends(get_db)):
    result = DeliverabilityService(db).campaign_readiness(campaign_id)
    if any(blocker.get("code") == "campaign_not_found" for blocker in result.get("blockers", [])):
        raise HTTPException(status_code=404, detail="Campaign not found")
    return result
