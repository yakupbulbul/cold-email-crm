from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.models.core import Domain

router = APIRouter()

class DomainCreate(BaseModel):
    name: str

@router.get("/")
@router.get("")  # Handle both /domains and /domains/ without redirect
def list_domains(db: Session = Depends(get_db)):
    return db.query(Domain).all()

@router.post("/")
@router.post("")  # Handle both /domains and /domains/ without redirect
def create_domain(req: DomainCreate, db: Session = Depends(get_db)):
    existing = db.query(Domain).filter(Domain.name == req.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Domain already exists")
    domain = Domain(name=req.name)
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain

@router.get("/{domain_id}")
def get_domain(domain_id: str, db: Session = Depends(get_db)):
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain
