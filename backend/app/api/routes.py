from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import models
from app.schemas import (
    DomainCreate, DomainResponse, MailboxCreate, MailboxResponse,
    ContactCreate, ContactResponse, CampaignCreate, CampaignResponse
)

router = APIRouter()

@router.post("/domains/", response_model=DomainResponse)
def create_domain(domain: DomainCreate, db: Session = Depends(get_db)):
    db_domain = models.Domain(name=domain.name)
    db.add(db_domain)
    db.commit()
    db.refresh(db_domain)
    return db_domain

@router.get("/domains/", response_model=list[DomainResponse])
def get_domains(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Domain).offset(skip).limit(limit).all()

@router.post("/mailboxes/", response_model=MailboxResponse)
def create_mailbox(mailbox: MailboxCreate, db: Session = Depends(get_db)):
    db_domain = db.query(models.Domain).filter(models.Domain.id == mailbox.domain_id).first()
    if not db_domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    
    db_mailbox = models.Mailbox(**mailbox.dict())
    db.add(db_mailbox)
    db.commit()
    db.refresh(db_mailbox)
    return db_mailbox

@router.get("/mailboxes/", response_model=list[MailboxResponse])
def get_mailboxes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Mailbox).offset(skip).limit(limit).all()

@router.post("/contacts/", response_model=ContactResponse)
def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    db_contact = models.Contact(**contact.dict())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

@router.get("/contacts/", response_model=list[ContactResponse])
def get_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Contact).offset(skip).limit(limit).all()

@router.post("/campaigns/", response_model=CampaignResponse)
def create_campaign(campaign: CampaignCreate, db: Session = Depends(get_db)):
    db_campaign = models.Campaign(**campaign.dict())
    db.add(db_campaign)
    db.commit()
    db.refresh(db_campaign)
    return db_campaign

@router.get("/campaigns/", response_model=list[CampaignResponse])
def get_campaigns(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.Campaign).offset(skip).limit(limit).all()
